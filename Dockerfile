# Container image for the Vector Guard prediction service.
# TODO: install deps, copy predict.py + model artifact, expose the API port.
# See README § Deployment for build/run instructions (to be filled in).

FROM python:3.12-slim

WORKDIR /app

# Placeholder — replace once predict.py and dependency pins for serving are ready.
CMD ["python", "-c", "raise SystemExit('Dockerfile not configured yet; see README Deployment')"]
