"""GCP Cloud Function HTTP entry.

Deploy:
    gcloud functions deploy linebot \
        --gen2 --runtime=python311 --region=asia-east1 \
        --source=. --entry-point=linebot \
        --trigger-http --allow-unauthenticated \
        --env-vars-file=.env.yaml

After deploy, copy the function URL and append /webhook into LINE
Developers Console (Messaging API > Webhook URL).
"""
import functions_framework

from app import create_app

_flask_app = create_app()


@functions_framework.http
def linebot(request):
    with _flask_app.request_context(request.environ):
        try:
            response = _flask_app.full_dispatch_request()
        except Exception as e:
            response = _flask_app.handle_exception(e)
        return response
