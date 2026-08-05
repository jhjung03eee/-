from app.rag.chunker import chunk_markdown
from app.rag.parser import extract_facts, parse_krw, split_sections, to_markdown

NOTICE = """# 테스트 공고

## 1. 사업 개요

- 사업명: 테스트 데이터 플랫폼 구축
- 발주기관: 테스트시청
- 사업예산: 1,250,000,000원
- 사업기간: 계약체결일로부터 10개월
- 사업지역: 서울특별시

## 5. 입찰참가 자격요건

- 소프트웨어사업자 신고를 필한 업체
- ISO 27001 인증을 보유한 업체

## 7. 제안서 평가 기준

- 기술평가 90점, 가격평가 10점
"""


def test_parse_krw_handles_korean_units():
    assert parse_krw("12억원") == 1_200_000_000
    assert parse_krw("3억 5,000만원") == 350_000_000
    assert parse_krw("1,250,000,000원") == 1_250_000_000
    assert parse_krw("금액 미정") is None


def test_extract_facts_reads_labeled_fields():
    facts = extract_facts(NOTICE)
    assert facts.title == "테스트 데이터 플랫폼 구축"
    assert facts.agency == "테스트시청"
    assert facts.budget_krw == 1_250_000_000
    assert facts.region == "서울특별시"
    assert facts.duration == "계약체결일로부터 10개월"
    assert len(facts.qualifications) == 2
    assert facts.evaluation_criteria


def test_split_sections_keeps_headings():
    titles = [title for title, _ in split_sections(NOTICE)]
    assert "1. 사업 개요" in titles
    assert "5. 입찰참가 자격요건" in titles


def test_chunks_have_unique_ids_and_sections():
    chunks = chunk_markdown(NOTICE, chunk_size=200, overlap=40)
    assert chunks
    assert len({c.chunk_id for c in chunks}) == len(chunks)
    assert all(c.section for c in chunks)
    assert all(len(c.text) <= 250 for c in chunks)


def test_to_markdown_promotes_plain_text_headings():
    plain = "1. 사업 개요\n내용입니다.\n□ 입찰참가자격\n자격 내용"
    markdown = to_markdown(plain, "notice.txt")
    assert "## 사업 개요" in markdown
    assert "## 입찰참가자격" in markdown
