FROM python:3.12-slim

WORKDIR /opt/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# BokehJS ships inside the bokeh pip package itself - vendor it into our own
# static/ rather than pulling it from a CDN, keeping the app self-hosted
# with no runtime external dependency. Copied here (not committed to git)
# so it always matches whatever bokeh version requirements.txt pins.
RUN mkdir -p app/static/js/bokeh && \
    BOKEH_STATIC=$(python -c "import bokeh, os; print(os.path.join(os.path.dirname(bokeh.__file__), 'server', 'static', 'js'))") && \
    cp "$BOKEH_STATIC/bokeh.min.js" "$BOKEH_STATIC/bokeh-tables.min.js" app/static/js/bokeh/

RUN chmod +x docker-entrypoint.sh

VOLUME ["/data"]
EXPOSE 5000

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["web"]
