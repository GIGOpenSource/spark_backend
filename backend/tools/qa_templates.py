"""她说推荐题库 — CN-first templates for QA gate ask flow. DB overrides static list."""

QA_TEMPLATES_ZH = [
    {'id': 'q1', 'text': '最近一次让你开心到想分享的小事是什么？', 'tags': ['日常']},
    {'id': 'q2', 'text': '理想的周末一天，你会怎么安排？', 'tags': ['生活']},
    {'id': 'q3', 'text': '你觉得一段关系里最重要的是什么？', 'tags': ['价值观']},
    {'id': 'q4', 'text': '如果只能推荐一部电影/一本书给我，会是什么？为什么？', 'tags': ['兴趣']},
    {'id': 'q5', 'text': '你通常怎么表达喜欢一个人？', 'tags': ['情感']},
    {'id': 'q6', 'text': '最近有没有一件事让你重新认识了自己？', 'tags': ['成长']},
    {'id': 'q7', 'text': '你理想的第一次见面会是怎样的？', 'tags': ['约会']},
    {'id': 'q8', 'text': '什么时候会让你觉得「这个人很有意思」？', 'tags': ['性格']},
    {'id': 'q9', 'text': '工作之外，你最想坚持去做的一件事是？', 'tags': ['兴趣']},
    {'id': 'q10', 'text': '如果明天突然多出一天假期，你最想做什么？', 'tags': ['日常']},
    {'id': 'q11', 'text': '你最欣赏朋友身上的哪种品质？', 'tags': ['价值观']},
    {'id': 'q12', 'text': '有没有一句口头禅或座右铭，能代表现在的你？', 'tags': ['性格']},
]

QA_TEMPLATES_EN = [
    {'id': 'q1', 'text': 'What small thing recently made you smile?', 'tags': ['daily']},
    {'id': 'q2', 'text': 'What does your ideal weekend look like?', 'tags': ['life']},
    {'id': 'q3', 'text': 'What matters most to you in a relationship?', 'tags': ['values']},
    {'id': 'q4', 'text': 'One movie or book you’d recommend — and why?', 'tags': ['interest']},
    {'id': 'q5', 'text': 'How do you usually show you like someone?', 'tags': ['feelings']},
]


def list_qa_templates(locale='zh', app_id=''):
    loc = (locale or 'zh').lower().split('-')[0]
    try:
        from models.models import QaTemplate
        qs = QaTemplate.objects.filter(enabled=True)
        if app_id:
            qs = qs.filter(app_id__in=['', app_id])
        else:
            qs = qs.filter(app_id='')
        if loc.startswith('zh'):
            qs = qs.filter(locale__istartswith='zh')
        else:
            qs = qs.filter(locale__istartswith=loc[:2] if loc else 'en')
        rows = list(qs.order_by('sort', 'id')[:50])
        if rows:
            return [
                {'id': f'db_{r.id}', 'text': r.text, 'tags': r.tags or []}
                for r in rows
            ]
    except Exception:
        pass
    if loc.startswith('zh'):
        return list(QA_TEMPLATES_ZH)
    return list(QA_TEMPLATES_EN)
