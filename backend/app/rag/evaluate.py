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

Modification History:
- 2026-06-15 (김민정): 최초 작성.
- 2026-06-16 (김민정): SAMPLE_INDICES 추가 (카테고리별 대표 문항 20개 평가).
"""

import json
import os
from pathlib import Path
from dotenv import load_dotenv
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
from ragas.embeddings import OpenAIEmbeddings as RagasOpenAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import openai
from backend.app.rag.retriever import search

load_dotenv()

DATASET_PATH = Path("data/ragas_dataset.json")

# 카테고리별 대표 문항 인덱스 (50개 중 20개 선택)
# 연차(4) + 육아휴직(4) + 연말정산(3) + 근로시간(4) + 출산휴가(2) + 일반HR(3)
SAMPLE_INDICES = [0, 2, 5, 8, 10, 11, 15, 17, 20, 22, 26, 28, 29, 30, 34, 38, 39, 42, 44, 49]


def build_ragas_dataset() -> Dataset:
    """
    ragas_dataset.json의 질문을 RAG로 실행해서 RAGAS용 데이터셋 생성.
    질문마다 RAG 검색을 실행하고 answer + contexts를 수집.
    """
    llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL"), temperature=0)

    with open(DATASET_PATH, encoding="utf-8") as f:
        raw = json.load(f)

    # 대표 문항만 선택
    raw = [raw[i] for i in SAMPLE_INDICES if i < len(raw)]

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
    """RAGAS 평가 실행 후 점수 출력 및 파일 저장."""
    print("데이터셋 준비 중...")
    dataset = build_ragas_dataset()

    # answer_relevancy는 embed_query 메서드가 필요 → ragas 클래스에 없어서 래퍼 추가
    openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    base_emb = RagasOpenAIEmbeddings(client=openai_client)
    base_emb.embed_query = base_emb.embed_text          # 메서드명 호환 패치
    base_emb.embed_documents = base_emb.embed_texts    # 메서드명 호환 패치
    answer_relevancy.embeddings = base_emb

    print("\nRAGAS 평가 시작...")
    result = evaluate(
        dataset=dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
    )

    # 새 RAGAS 버전은 항목별 점수 리스트를 반환 → 평균 계산
    df = result.to_pandas()
    scores = {
        "faithfulness": float(df["faithfulness"].mean()),
        "answer_relevancy": float(df["answer_relevancy"].mean()),
        "context_precision": float(df["context_precision"].mean()),
        "context_recall": float(df["context_recall"].mean()),
    }

    print("\n===== RAGAS 평가 결과 =====")
    print(f"Faithfulness      (환각 억제): {scores['faithfulness']:.4f}")
    print(f"Answer Relevancy  (답변 관련성): {scores['answer_relevancy']:.4f}")
    print(f"Context Precision (검색 정밀도): {scores['context_precision']:.4f}")
    print(f"Context Recall    (검색 재현율): {scores['context_recall']:.4f}")
    print("===========================")
    print("* 0에 가까울수록 낮음, 1에 가까울수록 높음")

    # 결과를 파일로 저장
    result_path = Path("data/ragas_result.json")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(scores, f, ensure_ascii=False, indent=2)
    print(f"\n결과 저장 완료: {result_path}")

    return result


if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore")
    run_evaluation()
