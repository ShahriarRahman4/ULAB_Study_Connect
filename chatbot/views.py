import json

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import TemplateView

from .engine import markdown_to_html, reply


SESSION_KEY = "nova_chat_history"
MAX_TURNS = 24


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ChatPageView(TemplateView):
    template_name = "chatbot/chat.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["history"] = self.request.session.get(SESSION_KEY, [])
        return ctx


class ChatApiView(View):
    def post(self, request):
        try:
            data = json.loads(request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            data = {}
        message = (data.get("message") or "").strip()
        if len(message) > 4000:
            message = message[:4000]
        if not message:
            return JsonResponse({"ok": False, "error": "Type a message first."}, status=400)

        history = list(request.session.get(SESSION_KEY, []))
        result = reply(message, history)
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": result["reply"]})
        request.session[SESSION_KEY] = history[-MAX_TURNS:]
        request.session.modified = True
        return JsonResponse({
            "ok": True,
            "reply": result["reply"],
            "reply_html": markdown_to_html(result["reply"]),
            "source": result.get("source", "nova"),
        })


class ChatClearView(View):
    def post(self, request):
        request.session[SESSION_KEY] = []
        request.session.modified = True
        return JsonResponse({"ok": True})
