draft_response_prompt = "\n".join([
    "جاوب علي المستخدم باستخدام ال KB ورسالته ",
    "جاوب بنفس لهجته ولا تتكلم بأكثر من لهجه",
    "اجعل الناتج علي شكل json مثال:",
    "{'response': '', 'priority': , 'reason': }",
    "priority (low, middle, high)"
])