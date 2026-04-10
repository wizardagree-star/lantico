"""
Lantico MVP — Models
Шкалы: KIND, WILL, IQ, HON (по 4 кейса на каждую, всего 16).
"""

import uuid
import statistics
from django.db import models


class Dimension(models.TextChoices):
    KIND = "KIND", "Доброта"
    WILL = "WILL", "Воля"
    IQ = "IQ", "Ум"
    HON = "HON", "Честность"


class Case(models.Model):
    """Проективная ситуация (кейс). 16 штук в MVP."""

    case_id = models.CharField(max_length=20, unique=True, db_index=True)  # e.g. kind_01
    dimension = models.CharField(max_length=4, choices=Dimension.choices)
    order = models.PositiveSmallIntegerField(help_text="Порядок показа (1-16)")
    situation_text = models.TextField(help_text="Текст ситуации")

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.case_id} [{self.dimension}]"


class Option(models.Model):
    """Вариант ответа (5 на кейс). Каждый имеет вес (raw_score)."""

    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="options")
    number = models.PositiveSmallIntegerField(help_text="1-5")
    text = models.TextField()
    raw_score = models.PositiveSmallIntegerField(
        help_text="Балл: 1-10 (для IQ: строго 2, 6 или 10)"
    )

    class Meta:
        ordering = ["case", "number"]
        unique_together = ("case", "number")

    def __str__(self):
        return f"{self.case.case_id} opt#{self.number} ({self.raw_score})"


class TestSession(models.Model):
    """Одна завершённая сессия тестирования."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.CharField(max_length=64, default="anonymous")
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return str(self.id)

    # ── Расчёт результатов ─────────────────────────────────────────

    def compute_results(self) -> dict:
        """
        Возвращает dict по формату Data_Schema.json → results + vector_signature.
        КРИТИЧНО: разная логика для KIND/WILL/HON (медиана+дисперсия) и IQ (среднее).
        """
        answers = self.answers.select_related("case").all()
        by_dim: dict[str, list[int]] = {}
        for a in answers:
            by_dim.setdefault(a.dimension, []).append(a.raw_score)

        results = {}
        vector = {}

        for dim in (Dimension.KIND, Dimension.WILL, Dimension.HON):
            scores = by_dim.get(dim, [])
            if not scores:
                continue
            med = statistics.median(scores)
            var = statistics.pvariance(scores)  # популяционная дисперсия
            results[dim] = {
                "median": med,
                "variance": round(var, 2),
                "interpretation": _interpret(dim, med),
                "is_situational": var > 4.0,
            }
            vector[dim] = round(med)

        # IQ — среднее арифметическое, correct_answers = кол-во 10-ок
        iq_scores = by_dim.get(Dimension.IQ, [])
        if iq_scores:
            avg = sum(iq_scores) / len(iq_scores)
            results[Dimension.IQ] = {
                "average_score": round(avg, 2),
                "correct_answers": iq_scores.count(10),
                "total_questions": len(iq_scores),
                "interpretation": _interpret(Dimension.IQ, avg),
            }
            vector[Dimension.IQ] = round(avg)

        return {"results": results, "vector_signature": vector}


class Answer(models.Model):
    """Один ответ пользователя на кейс."""

    session = models.ForeignKey(
        TestSession, on_delete=models.CASCADE, related_name="answers"
    )
    case = models.ForeignKey(Case, on_delete=models.CASCADE)
    dimension = models.CharField(max_length=4, choices=Dimension.choices)
    selected_option = models.PositiveSmallIntegerField()
    raw_score = models.PositiveSmallIntegerField()

    class Meta:
        unique_together = ("session", "case")


# ── Интерпретация ──────────────────────────────────────────────────

SITUATIONAL_NOTE = (
    "Ваше поведение в этой сфере сильно зависит от ситуации и настроения. "
    "В одних обстоятельствах вы проявляете это качество ярко, "
    "в других — почти не используете."
)

_TEXTS = {
    Dimension.KIND: [
        (3, "Прагматик. Вы ставите свои интересы превыше всего. Это помогает в бизнесе, но может отталкивать людей. Вы редко действуете во вред себе ради других."),
        (5, "Избирательная эмпатия. Вы помогаете, когда это не требует серьёзных жертв. Близким с вами комфортно, чужим — не очень."),
        (7, "Разумный эгоист с эмпатией. Вы помогаете, но не в ущерб собственным границам. Вы не дадите себя эксплуатировать, но в критической ситуации на вас можно положиться."),
        (10, "Альтруист. Потребности других для вас так же важны, как свои. Окружающие это ценят, но есть риск эмоционального выгорания из-за чрезмерной самоотдачи."),
    ],
    Dimension.WILL: [
        (3, "Ведомый. Вы легко отказываетесь от целей при первых трудностях. Вам нужна внешняя мотивация и контроль, чтобы доводить дела до конца."),
        (5, "Ситуативная воля. Если цель зажигает — вы горы свернёте. Если задача скучная — вы быстро теряете интерес и переключаетесь."),
        (7, "Дисциплинированный. Вы умеете заставлять себя делать то, что надо, но иногда даёте себе поблажки. Хороший баланс между усилием и отдыхом."),
        (10, "Стальной стержень. Вы способны достигать целей вопреки лени и обстоятельствам. Окружающие могут считать вас упёртым. Осторожно: риск выгорания."),
    ],
    Dimension.IQ: [
        (4, "Практик. Вы предпочитаете действовать по проверенным шаблонам. Абстрактные задачи вызывают трудности, но в знакомой среде вы эффективны."),
        (7, "Сообразительный. Вы хорошо решаете бытовые и рабочие задачи, но сложные логические конструкции могут требовать больше времени."),
        (10, "Аналитик. Вы быстро схватываете суть, видите закономерности и умеете отделять причины от следствий. Высокий потенциал к обучению и сложной интеллектуальной работе."),
    ],
    Dimension.HON: [
        (3, "Гибкий прагматик. Вы считаете, что правда — понятие относительное. Ложь во спасение или для выгоды для вас допустима, если нет риска разоблачения."),
        (5, "Дипломат. Вы стараетесь не врать без нужды, но можете умолчать или смягчить правду, чтобы избежать конфликта или неудобных последствий."),
        (7, "Честный, но с оглядкой. Вы цените правду, но в сложной ситуации можете поколебаться. Вы не станете врать ради выгоды, но иногда выбираете безопасность вместо истины."),
        (10, "Принципиальный. Правда для вас — фундаментальная ценность. Вы говорите как есть, даже если это вредит вашим интересам. Люди знают, что на ваше слово можно положиться."),
    ],
}


def _interpret(dimension: str, score: float) -> str:
    for upper, text in _TEXTS[dimension]:
        if score <= upper:
            return text
    return _TEXTS[dimension][-1][1]
