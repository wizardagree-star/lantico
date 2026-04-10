"""
Lantico MVP — API views + page views (single-server deployment).
"""

from django.shortcuts import render
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Answer, Case, Dimension, Option, TestSession


# ── Serializers ────────────────────────────────────────────

class OptionOutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ("number", "text")


class CaseOutSerializer(serializers.ModelSerializer):
    options = OptionOutSerializer(many=True, read_only=True)

    class Meta:
        model = Case
        fields = ("case_id", "dimension", "order", "situation_text", "options")


class AnswerInSerializer(serializers.Serializer):
    case_id = serializers.CharField()
    selected_option = serializers.IntegerField(min_value=1, max_value=5)


class SubmitSerializer(serializers.Serializer):
    answers = AnswerInSerializer(many=True)

    def validate_answers(self, value):
        if len(value) != 16:
            raise serializers.ValidationError("Ожидается ровно 16 ответов.")
        return value


# ── API Views ──────────────────────────────────────────────

@api_view(["GET"])
def questions_list(request):
    cases = Case.objects.prefetch_related("options").order_by("order")
    return Response(CaseOutSerializer(cases, many=True).data)


@api_view(["POST"])
def submit_test(request):
    ser = SubmitSerializer(data=request.data)
    ser.is_valid(raise_exception=True)

    session = TestSession.objects.create()
    answers_in = ser.validated_data["answers"]

    case_ids = [a["case_id"] for a in answers_in]
    cases = Case.objects.filter(case_id__in=case_ids)
    case_map = {c.case_id: c for c in cases}

    options = Option.objects.filter(case__case_id__in=case_ids)
    opt_map = {}
    for o in options:
        opt_map[(o.case.case_id, o.number)] = o

    bulk = []
    for a in answers_in:
        cid = a["case_id"]
        num = a["selected_option"]
        case = case_map.get(cid)
        if not case:
            return Response({"error": f"Неизвестный case_id: {cid}"}, status=status.HTTP_400_BAD_REQUEST)
        opt = opt_map.get((cid, num))
        if not opt:
            return Response({"error": f"Нет опции {num} для {cid}"}, status=status.HTTP_400_BAD_REQUEST)
        bulk.append(Answer(
            session=session, case=case, dimension=case.dimension,
            selected_option=num, raw_score=opt.raw_score,
        ))

    Answer.objects.bulk_create(bulk)
    session.completed_at = timezone.now()
    session.save(update_fields=["completed_at"])

    computed = session.compute_results()
    return Response({
        "session_id": str(session.id),
        "started_at": session.started_at,
        "completed_at": session.completed_at,
        **computed,
    }, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def result_detail(request, session_id):
    try:
        session = TestSession.objects.get(pk=session_id)
    except (TestSession.DoesNotExist, ValueError):
        return Response({"error": "Сессия не найдена"}, status=status.HTTP_404_NOT_FOUND)

    computed = session.compute_results()
    answers_out = [
        {"case_id": a.case.case_id, "dimension": a.dimension,
         "selected_option": a.selected_option, "raw_score": a.raw_score}
        for a in session.answers.select_related("case").all()
    ]
    return Response({
        "session_id": str(session.id),
        "user_id": session.user_id,
        "started_at": session.started_at,
        "completed_at": session.completed_at,
        "answers": answers_out,
        **computed,
    })


# ── Page Views (HTML templates) ────────────────────────────

def landing_page(request):
    return render(request, "landing.html")


def test_page(request):
    return render(request, "test.html")


def result_page(request, session_id):
    return render(request, "result.html", {"session_id": session_id})
