import re
import openai
import streamlit as st
from supabase import create_client
import threading

openai.api_key = st.secrets.OPENAI_TOKEN
openai_model_version = "gpt-3.5-turbo"

col1, col2, col3 = st.columns([1, 6, 1])
with col1:
    st.image('./data/python.png', width=100)
with col2:
    st.markdown("<h1 style='text-align: center;'>Python Quiz</h1>", unsafe_allow_html=True)
with col3:
    st.image('./data/python.png', width=100)

st.markdown("<div style='text-align: center;'><h3>AI와 함께 당신의 파이썬 실력을 업그레이드하세요!</h3></div>", unsafe_allow_html=True)
st.markdown("<div style='text-align: right;'>(Powered by {})</div>".format(openai_model_version), unsafe_allow_html=True)
st.write("")

@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

def write_prompt_result(prompt, result):
    data = supabase.table("python quiz")\
        .insert({"prompt": prompt, "results": result})\
        .execute()
    print(data)

def write_prompt_result_with_supabase(prompt, answer):
    write_prompt_result(prompt, answer)

supabase = init_connection()

def generate_prompt(difficulty):
    prompt = f'''파이썬 코드를 학습하는 데 도움을 줄 수 있는 4지선다형 문제를 {difficulty} 난이도에 맞춰 1개 생성해주세요. 억지로 만든 듯한 문제는 내지 말고, 각각의 보기가 맞고 틀리는 이유가 누가 보더라도 명쾌하고 합당해야 합니다. 문제의 난이도는 상, 중, 하 레벨에 맞춰 어렵거나 쉬워야 합니다. 아래와 같은 형식에 따라 문제와 답변을 제시해 주세요. 보기는 반드시 (1) (2) (3) (4)로 시작해야 합니다:
<문제>
문제 내용

<보기>
(1) 선택지 1
(2) 선택지 2
(3) 선택지 3
(4) 선택지 4

<정답>
(번호)

<해설>
해설 내용'''
    return prompt.strip()

def request_chat_completion(prompt):
    response = openai.ChatCompletion.create(
        model=openai_model_version,
        messages=[
            {'role': 'system', 'content': '당신은 유용한 도우미입니다.'},
            {'role': 'user', 'content': prompt}]
    )
    return response['choices'][0]['message']['content']

def format_choices(choices_text):
    choices = re.findall(r'\(\d\)(?:.*\n?)*?(?=\(\d\)|\Z)', choices_text)
    formatted_choices = []

    for choice in choices:
        choice = re.sub("\n```python\n|\n```\n", " ", choice)
        choice = choice.replace("```", "")
        choice = choice.strip()

        lines = choice.splitlines()
        first_line = lines[0].rstrip()
        other_lines = " | ".join(line.strip() for line in lines[1:] if line.strip())
        formatted_choice = f'{first_line} {other_lines}'.lstrip()

        formatted_choices.append(formatted_choice.strip())

    return formatted_choices

def parse_input(answer_text):
    question_match = re.search(r'(?i)<\s?문제\s?>[:]*\s*(.*?)<\s?보기\s?>', answer_text, re.DOTALL)
    choices_match = re.search(r'(?i)<\s?보기\s?>[:]*\s*(.*?)<\s?정답\s?>', answer_text, re.DOTALL)
    correct_answer_match = re.search(r'(?i)<\s?정답\s?>[:]*\s*(\(\d\))', answer_text)
    if correct_answer_match:
        correct_answer = correct_answer_match.group(1)
    explanation_match = re.search(r'(?i)<\s?해설\s?>[:]*\s*(.*)', answer_text, re.DOTALL)

    if not question_match or not choices_match or not correct_answer_match:
        question_part, sep, choices_part = answer_text.partition("보기")
        choices_part, sep, rest = choices_part.partition("정답")
        correct_answer_part, sep, explanation_part = rest.partition("해설")
        
        question = question_part.replace("문제:", "").strip()
        choices_text = choices_part.strip()
        correct_answer = correct_answer_part.strip()
        explanation = explanation_part.strip()
    else:
        question = question_match.group(1).strip()
        choices_text = choices_match.group(1).strip()
        correct_answer = correct_answer_match.group(1).strip()
        explanation = explanation_match.group(1).strip()

    formatted_choices = format_choices(choices_text)
    formatted_question = question.strip()
    formatted_correct_answer = correct_answer.strip()
    formatted_explanation = explanation.strip()
    return formatted_question, formatted_choices, formatted_correct_answer, formatted_explanation

difficulty = st.selectbox("난이도 선택", ["상", "중", "하"], key="difficulty_key")
st.write("")

if 'new_question' not in st.session_state:
    st.session_state.new_question = False
if 'not_selected_yet' not in st.session_state:
    st.session_state.not_selected_yet = True
if 'question' not in st.session_state:
    st.session_state.question = ""
if 'choices' not in st.session_state:
    st.session_state.choices = []

if st.button("문제를 주세요", key="new_question_button"):
    prompt = generate_prompt(difficulty)

    with st.spinner('AI가 문제를 출제 중입니다'):
        answer = request_chat_completion(prompt)
        thread = threading.Thread(target=write_prompt_result_with_supabase, args=(prompt, answer))
        thread.start()
        question, choices, correct_answer, explanation = parse_input(answer)

    st.session_state.choices = choices
    st.session_state.correct_answer = correct_answer
    st.session_state.explanation = explanation
    st.session_state.question = question
    st.session_state.not_selected_yet = True

if st.session_state.question:
    st.markdown(f"**문제**: {st.session_state.question}")

    if st.session_state.choices:
        response = st.radio(
            "보기:",
            st.session_state.choices,
            key="radio_choice",
            label_visibility="collapsed"
        )
        selected_choice = (
            response.strip().split(") ")[0][1:] if response else ""
        )
        
        if st.button("제출", key="submit_button"):
            st.write(f"선택한 답: ({selected_choice})")

            if selected_choice == st.session_state.correct_answer.strip('()'):
                st.success("정답입니다!")
            else:
                st.warning("오답입니다.")
            st.write(f"정답: {st.session_state.correct_answer}")
            st.markdown(f"**해설**: {st.session_state.explanation}")

            st.session_state.not_selected_yet = False