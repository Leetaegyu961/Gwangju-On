"""
Agent Main
에이전트 실행 진입점입니다.
"""

import asyncio
from langchain_core.messages import HumanMessage

from .config import config
from .graph import create_agent_graph


async def run_agent(user_input: str) -> str:
    """
    에이전트를 실행합니다. (Async)

    Args:
        user_input: 사용자 입력 문자열

    Returns:
        에이전트의 최종 응답
    """
    # 설정 검증
    config.validate()

    # 그래프 생성
    graph = create_agent_graph()

    # 초기 상태 설정
    initial_state = {
        "messages": [HumanMessage(content=user_input)],
        "current_step": "thinking",
        "tool_results": None,
        "query_plan": None,
        "place_data": None,
        "enriched_results": None,
        "final_answer": None,
    }

    # 그래프 실행 (async)
    if config.VERBOSE:
        print(f"🤖 에이전트 시작: {user_input}")

    result = await graph.ainvoke(initial_state)

    final_answer = result.get("final_answer", "응답을 생성하지 못했습니다.")

    if config.VERBOSE:
        print(f"✅ 최종 응답: {final_answer}")

    return final_answer


def main():
    """메인 함수 - CLI 인터페이스"""
    print("=" * 50)
    print("🚀 AI Agent에 오신 것을 환영합니다!")
    print("=" * 50)
    print("종료하려면 'quit' 또는 'exit'를 입력하세요.\n")

    while True:
        try:
            user_input = input("👤 You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ["quit", "exit", "종료"]:
                print("👋 안녕히 가세요!")
                break

            response = asyncio.run(run_agent(user_input))
            print(f"\n🤖 Agent: {response}\n")

        except KeyboardInterrupt:
            print("\n👋 안녕히 가세요!")
            break
        except Exception as e:
            print(f"❌ 오류 발생: {e}\n")


if __name__ == "__main__":
    main()
