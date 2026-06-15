"""
File    : backend/app/rag/evaluate.py
Author  : 김민정
Create  : 2026-06-15
Description :
    RAGAS를 사용해 RAG 파이프라인 품질을 측정.
    data/ragas_dataset.json의 질문을 RAG로 실행하고 점수를 출력.

    측정 항목:
    - faithfulness     : 답변이 검색된 문서에 근거하는가 (환각 여부)
    - answer_relevancy : 답변이 질문에 적절한가
    - context_precision: 검색된 청크가 질문에 관련 있는가
    - context_recall   : 정답에 필요한 내용이 검색됐는가
"""

import json
import os
from pathlib import Path
from dotenv import load_dotenv
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from backend.app.rag.retriever import search

load_dotenv()

DATASET_PATH = Path("data/ragas_dataset.json")


def build_ragas_dataset() -> Dataset:
    """
    ragas_dataset.json의 질문을 RAG로 실행해서 RAGAS용 데이터셋 생성.
    질문마다 RAG 검색을 실행하고 answer + contexts를 수집.
    """
    llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL"), temperature=0)

    with open(DATASET_PATH, encoding="utf-8") as f:
        raw = json.load(f)

    questions, answers, contexts, ground_truths = [], [], [], []

    for i, item in enumerate(raw, 1):
        question = item["question"]
        ground_truth = item["ground_truth"]
        print(f"[{i}/{len(raw)}] 질문 실행 중: {question[:40]}")

        # RAG 검색
        chunks = search(question)
        context_texts = [c["text"] for c in chunks]
        context = "\n\n".join(context_texts)

        # LLM 답변 생성
        messages = [
            SystemMessage(content=f"""
                아래 문서를 참고해서 질문에 답하세요.
                문서에 없는 내용은 답하지 마세요.

                [참고 문서]
                {context}
            """),
            HumanMessage(content=question),
        ]
        response = llm.invoke(messages)

        questions.append(question)
        answers.append(response.content)
        contexts.append(context_texts)
        ground_truths.append(ground_truth)

    return Dataset.from_dict({
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truth": ground_truths,
    })


def run_evaluation():
    """RAGAS 평가 실행 후 점수 출력."""
    print("데이터셋 준비 중...")
    dataset = build_ragas_dataset()

    print("\nRAGAS 평가 시작...")
    result = evaluate(
        dataset=dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
    )

    print("\n===== RAGAS 평가 결과 =====")
    print(f"Faithfulness      (환각 억제): {result['faithfulness']:.4f}")
    print(f"Answer Relevancy  (답변 관련성): {result['answer_relevancy']:.4f}")
    print(f"Context Precision (검색 정밀도): {result['context_precision']:.4f}")
    print(f"Context Recall    (검색 재현율): {result['context_recall']:.4f}")
    print("===========================")
    print("* 0에 가까울수록 낮음, 1에 가까울수록 높음")

    return result


if __name__ == "__main__":
    run_evaluation()
