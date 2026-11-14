"""H3 coverage maps for interim VectorNet detections."""

from __future__ import annotations

import json
from typing import Any

import folium
import h3
import pandas as pd
from branca.colormap import LinearColormap
from branca.element import MacroElement, Template

_REQUIRED_VECTOR_COLS = (
    "h3_cell",
    "year",
    "month",
    "record_id",
    "country_iso2",
    "vector_group",
)

_EMPTY_CELL_STATS_COLS = [
    "h3_cell",
    "vector_group",
    "n_year_months",
    "n_records",
    "n_years",
    "year_span",
    "year_min",
    "year_max",
]

_POPUP_METRICS = (
    "n_year_months",
    "n_years",
    "year_span",
    "n_records",
    "year_min",
    "year_max",
)

# OSM raster tiles (street basemap). Explicit URL keeps streets visible in notebooks.
_OSM_TILES = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
_OSM_ATTR = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'


class _PopupFilterByGroupLayers(MacroElement):
    """Wire LayerControl group overlays to combined-popup column filtering.

    Empty ``FeatureGroup`` overlays named after each vector_group act as toggles.
    Popup/tooltip HTML is rebuilt from ``groups_data`` using only active groups.
    """

    _template = Template(
        """
        {% macro script(this, kwargs) %}
            var {{ this.get_name() }}_active = {{ this.groups_json }};
            var {{ this.get_name() }}_metrics = {{ this.metrics_json }};

            {{ this.map_name }}.on("overlayadd", function (e) {
                if (Object.prototype.hasOwnProperty.call({{ this.get_name() }}_active, e.name)) {
                    {{ this.get_name() }}_active[e.name] = true;
                }
            });
            {{ this.map_name }}.on("overlayremove", function (e) {
                if (Object.prototype.hasOwnProperty.call({{ this.get_name() }}_active, e.name)) {
                    {{ this.get_name() }}_active[e.name] = false;
                }
            });

            function {{ this.get_name() }}_escape(text) {
                return String(text)
                    .replace(/&/g, "&amp;")
                    .replace(/</g, "&lt;")
                    .replace(/>/g, "&gt;")
                    .replace(/"/g, "&quot;");
            }

            function {{ this.get_name() }}_buildHtml(props) {
                var cellId = props.h3_cell || "";
                var allGroups = props.groups_data || [];
                var cols = allGroups.filter(function (row) {
                    return {{ this.get_name() }}_active[row.vector_group];
                });
                if (!cols.length) {
                    return (
                        "<div style='font-family:system-ui,sans-serif;font-size:12px;padding:4px'>"
                        + "<div style='font-weight:600;margin-bottom:4px'>H3 "
                        + {{ this.get_name() }}_escape(cellId) + "</div>"
                        + "<div>No vector groups selected in the layer control.</div>"
                        + "</div>"
                    );
                }
                var header = "<tr><th style='text-align:left;padding:4px 8px;"
                    + "border-bottom:1px solid #ccc'>metric</th>";
                cols.forEach(function (row) {
                    header += "<th style='text-align:center;padding:4px 8px;"
                        + "border-bottom:1px solid #ccc'>"
                        + {{ this.get_name() }}_escape(row.vector_group) + "</th>";
                });
                header += "</tr>";
                var body = "";
                {{ this.get_name() }}_metrics.forEach(function (metric) {
                    body += "<tr><td style='text-align:left;padding:3px 8px;"
                        + "border-bottom:1px solid #eee'>"
                        + {{ this.get_name() }}_escape(metric) + "</td>";
                    cols.forEach(function (row) {
                        var val = row[metric];
                        if (val === null || val === undefined) { val = "—"; }
                        body += "<td style='text-align:right;padding:3px 8px;"
                            + "border-bottom:1px solid #eee'>"
                            + {{ this.get_name() }}_escape(val) + "</td>";
                    });
                    body += "</tr>";
                });
                return (
                    "<div style='min-width:240px'>"
                    + "<div style='font-weight:600;margin-bottom:6px;"
                    + "font-family:system-ui,sans-serif'>H3 "
                    + {{ this.get_name() }}_escape(cellId) + "</div>"
                    + "<table style='border-collapse:collapse;font-size:12px;"
                    + "font-family:system-ui,sans-serif;white-space:nowrap'>"
                    + "<thead>" + header + "</thead><tbody>" + body + "</tbody></table>"
                    + "</div>"
                );
            }

            {{ this.geojson_name }}.eachLayer(function (layer) {
                if (!(layer.feature && layer.feature.properties)) { return; }
                layer.bindPopup(function (lyr) {
                    return {{ this.get_name() }}_buildHtml(lyr.feature.properties);
                }, { maxWidth: 640, className: "vector-guard-h3-popup" });
                layer.bindTooltip(function (lyr) {
                    return {{ this.get_name() }}_buildHtml(lyr.feature.properties);
                }, { sticky: true, opacity: 0.95, className: "vector-guard-h3-tooltip" });
            });
        {% endmacro %}
        """
    )

    def __init__(self, map_name: str, geojson_name: str, groups: list[str]) -> None:
        super().__init__()
        self._name = "PopupFilterByGroupLayers"
        self.map_name = map_name
        self.geojson_name = geojson_name
        self.groups_json = json.dumps({g: True for g in groups})
        self.metrics_json = json.dumps(list(_POPUP_METRICS))


def aggregate_interim_vector_cells(
    vectors: pd.DataFrame,
    *,
    country_iso2: str | None = None,
    vector_group: str | None = None,
) -> pd.DataFrame:
    """Aggregate interim vector rows to one row per ``(h3_cell, vector_group)``.

    Metrics:
    - ``n_year_months``: distinct ``(year, month)`` with ≥1 record
    - ``n_records``: row count
    - ``n_years``: distinct years
    - ``year_span``: ``max(year) - min(year) + 1`` (includes gaps)
    """
    missing = [c for c in _REQUIRED_VECTOR_COLS if c not in vectors.columns]
    if missing:
        raise ValueError(f"vectors missing required columns: {missing}")

    work = vectors.loc[vectors["h3_cell"].notna() & vectors["vector_group"].notna()].copy()
    if country_iso2 is not None:
        code = str(country_iso2).strip().upper()
        work = work.loc[work["country_iso2"].astype(str).str.upper() == code]
    if vector_group is not None:
        group = str(vector_group).strip()
        work = work.loc[work["vector_group"].astype(str) == group]

    # Frequency / duration metrics need usable year-month; drop incomplete dates.
    work = work.loc[work["year"].notna() & work["month"].notna()]

    if work.empty:
        return pd.DataFrame(columns=_EMPTY_CELL_STATS_COLS)

    keys = ["h3_cell", "vector_group"]
    grouped = work.groupby(keys, sort=False)
    stats = grouped.agg(
        n_records=("record_id", "size"),
        n_years=("year", "nunique"),
        year_min=("year", "min"),
        year_max=("year", "max"),
    )
    ym = (
        work.drop_duplicates(subset=["h3_cell", "vector_group", "year", "month"])
        .groupby(keys, sort=False)
        .size()
        .rename("n_year_months")
    )
    out = stats.join(ym, how="left")
    out["year_span"] = (out["year_max"] - out["year_min"] + 1).astype("int64")
    out = out.reset_index()
    return out[_EMPTY_CELL_STATS_COLS].sort_values(
        "n_year_months", ascending=False, ignore_index=True
    )


def _json_safe(val: Any) -> Any:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if hasattr(val, "item"):
        return val.item()
    return val


def _groups_data_records(group_rows: pd.DataFrame) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for row in group_rows.sort_values("vector_group").itertuples(index=False):
        rec: dict[str, Any] = {"vector_group": str(getattr(row, "vector_group"))}
        for metric in _POPUP_METRICS:
            rec[metric] = _json_safe(getattr(row, metric))
        records.append(rec)
    return records


def h3_cells_to_geojson(
    cell_stats: pd.DataFrame,
    value_col: str,
) -> dict[str, Any]:
    """Build a GeoJSON FeatureCollection: one feature per H3 cell.

    Fill ``value`` is ``max(value_col)`` across vector groups in the cell.
    ``groups_data`` holds per-group stats for the filtered combined popup.
    """
    if value_col not in cell_stats.columns:
        raise ValueError(f"value_col {value_col!r} not in cell_stats columns")
    if "h3_cell" not in cell_stats.columns:
        raise ValueError("cell_stats must include h3_cell")
    if "vector_group" not in cell_stats.columns:
        raise ValueError("cell_stats must include vector_group")

    features: list[dict[str, Any]] = []
    for cell_id, group_rows in cell_stats.groupby("h3_cell", sort=False):
        if cell_id is None or (isinstance(cell_id, float) and pd.isna(cell_id)):
            continue
        cell_str = str(cell_id)
        try:
            geometry = h3.cells_to_geo([cell_str])
        except Exception:
            continue
        values = pd.to_numeric(group_rows[value_col], errors="coerce").dropna()
        fill_value = float(values.max()) if not values.empty else None
        groups_data = _groups_data_records(group_rows)
        groups = [r["vector_group"] for r in groups_data]
        features.append(
            {
                "type": "Feature",
                "id": cell_str,
                "geometry": geometry,
                "properties": {
                    "h3_cell": cell_str,
                    "value": fill_value,
                    "n_groups": len(groups),
                    "groups": ", ".join(groups),
                    "groups_data": groups_data,
                },
            }
        )

    return {"type": "FeatureCollection", "features": features}


def _collect_bounds(geojson: dict[str, Any]) -> tuple[list[float], list[float]]:
    lats: list[float] = []
    lons: list[float] = []
    for feat in geojson.get("features") or []:
        geom = feat.get("geometry") or {}
        coords = geom.get("coordinates") or []
        gtype = geom.get("type")
        rings = coords if gtype == "Polygon" else [ring for poly in coords for ring in poly]
        for ring in rings:
            for lon_i, lat_i in ring:
                lats.append(lat_i)
                lons.append(lon_i)
    return lats, lons


def _base_map(lat: float, lon: float, zoom_start: int = 5) -> folium.Map:
    """Map with an explicit OpenStreetMap street basemap."""
    fmap = folium.Map(location=[lat, lon], zoom_start=zoom_start, tiles=None)
    folium.TileLayer(
        tiles=_OSM_TILES,
        attr=_OSM_ATTR,
        name="Streets",
        control=False,
        max_zoom=19,
        overlay=False,
    ).add_to(fmap)
    return fmap


def folium_h3_choropleth(
    cell_stats: pd.DataFrame,
    value_col: str,
    *,
    title: str | None = None,
    fill_opacity: float = 0.45,
    line_weight: float = 0.6,
) -> folium.Map:
    """Interactive Folium map of H3 cells colored by ``value_col``.

    One polygon per ``h3_cell`` on an OSM street basemap (shared color scale;
    fill = ``max(value_col)`` across groups in the cell).

    When multiple vector groups are present, a LayerControl lists each group.
    Those toggles do **not** remove hexes; they filter which group columns appear
    in the combined horizontal popup/tooltip.
    """
    if cell_stats.empty:
        return _base_map(50.0, 10.0, zoom_start=4)

    values = pd.to_numeric(cell_stats[value_col], errors="coerce").dropna()
    vmin = float(values.min()) if not values.empty else 0.0
    vmax = float(values.max()) if not values.empty else 1.0
    if vmin == vmax:
        vmax = vmin + 1.0

    caption = title or value_col
    if cell_stats["h3_cell"].nunique() < len(cell_stats):
        caption = f"{caption} (fill = max across groups)"

    colormap = LinearColormap(
        colors=["#f7fbff", "#6baed6", "#08306b"],
        vmin=vmin,
        vmax=vmax,
        caption=caption,
    )

    first_cell = str(cell_stats["h3_cell"].iloc[0])
    lat, lon = h3.cell_to_latlng(first_cell)
    fmap = _base_map(lat, lon, zoom_start=5)

    geojson = h3_cells_to_geojson(cell_stats, value_col)
    groups = sorted(
        str(g) for g in cell_stats["vector_group"].dropna().unique().tolist()
    )

    def _style(feature: dict[str, Any]) -> dict[str, Any]:
        raw = feature.get("properties", {}).get("value")
        try:
            val = float(raw) if raw is not None else vmin
        except (TypeError, ValueError):
            val = vmin
        return {
            "fillColor": colormap(val),
            "color": "#333333",
            "weight": line_weight,
            "fillOpacity": fill_opacity,
        }

    # Hex layer (kept out of the group-filter toggles).
    hex_group = folium.FeatureGroup(name="H3 cells", show=True)
    layer = folium.GeoJson(
        geojson,
        style_function=_style,
        name=title or value_col,
    )
    layer.add_to(hex_group)
    hex_group.add_to(fmap)

    # Empty overlays: LayerControl checkboxes filter popup columns only.
    if len(groups) >= 2:
        for group in groups:
            folium.FeatureGroup(name=group, show=True).add_to(fmap)
        folium.LayerControl(collapsed=False).add_to(fmap)
        fmap.add_child(
            _PopupFilterByGroupLayers(
                map_name=fmap.get_name(),
                geojson_name=layer.get_name(),
                groups=groups,
            )
        )
    else:
        # Single group (or none): bind popup with the same horizontal table helper.
        fmap.add_child(
            _PopupFilterByGroupLayers(
                map_name=fmap.get_name(),
                geojson_name=layer.get_name(),
                groups=groups,
            )
        )

    colormap.add_to(fmap)

    all_lats, all_lons = _collect_bounds(geojson)
    if all_lats and all_lons:
        fmap.fit_bounds([[min(all_lats), min(all_lons)], [max(all_lats), max(all_lons)]])

    return fmap
