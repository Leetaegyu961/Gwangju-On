
import { CoursePoint, SavedCourse, Message, EvidenceCard, CourseInfo } from "../types";
import { API_URL } from "../utils/apiConfig";

export class GeminiService {
  private apiUrl: string;

  constructor() {
    // Use centralized API config instead of duplicating env var logic
    this.apiUrl = API_URL;
  }

  async processRequest(input: string, onStatusChange?: (status: Message['status']) => void): Promise<Message> {
    if (onStatusChange) onStatusChange('analyzing');

    // userId 가져오기
    const userId = localStorage.getItem('temp_user_id') || undefined;

    try {
      console.log(`[GeminiService] Requesting to: ${this.apiUrl}/chat`);
      const response = await fetch(`${this.apiUrl}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: input, userId }),
      });

      if (!response.ok) {
        throw new Error('Network response was not ok');
      }

      if (onStatusChange) onStatusChange('generating');
      const data = await response.json();

      return {
        id: data.id,
        role: data.role as 'assistant',
        text: data.text,
        isDecisionPoint: data.isDecisionPoint,
        evidenceCards: data.evidenceCards,
        allCourses: data.allCourses,  // 3개 코스 전체 추가
        status: data.status as 'done'
      };
    } catch (error) {
      console.error('Error processing request:', error);
      return {
        id: Date.now().toString(),
        role: 'assistant',
        text: "죄송합니다. 서버와 연결하는 중에 문제가 발생했습니다.",
        status: 'done'
      };
    }
  }

  /**
   * SSE 스트리밍으로 Agent 진행 상황을 실시간 수신합니다.
   */
  async processRequestStream(
    input: string,
    onProgress?: (data: { step: string; message: string; progress: number; icon?: string }) => void
  ): Promise<Message> {
    const userId = localStorage.getItem('temp_user_id') || undefined;

    try {
      const response = await fetch(`${this.apiUrl}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: input, userId }),
      });

      if (!response.ok || !response.body) {
        throw new Error('Stream response failed');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let finalResult: any = null;
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split('\n\n');
        buffer = parts.pop() || '';

        for (const part of parts) {
          for (const line of part.split('\n')) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                if (data.step === 'done' || data.step === 'error') {
                  finalResult = data.result;
                } else if (onProgress) {
                  onProgress(data);
                }
              } catch (e) { /* ignore parse error */ }
            }
          }
        }
      }

      if (finalResult) {
        return {
          id: finalResult.id || Date.now().toString(),
          role: finalResult.role as 'assistant',
          text: finalResult.text,
          isDecisionPoint: finalResult.isDecisionPoint,
          evidenceCards: finalResult.evidenceCards,
          allCourses: finalResult.allCourses,
          status: 'done'
        };
      }
      throw new Error('No final result');
    } catch (error) {
      console.error('[GeminiService] Stream error, falling back:', error);
      return this.processRequest(input);
    }
  }

  async getUserProfile(): Promise<any> {
    const userId = localStorage.getItem('temp_user_id');
    const token = localStorage.getItem('access_token');

    // [New] 1. Try fetching with Token (/auth/me) - MOST RELIABLE for logged-in users
    if (token) {
      try {
        const res = await fetch(`${this.apiUrl}/auth/me`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        if (res.ok) {
          const data = await res.json();
          // If successful, update local storage to sync
          if (data.id) localStorage.setItem('temp_user_id', data.id);
          return data;
        }
        console.warn("⚠️ [GeminiService] /auth/me failed, falling back to ID check.");
      } catch (e) {
        console.error("Failed to fetch /auth/me", e);
      }
    }

    // 2. Fallback to ID-based fetch (Guest or if token fails)
    if (!userId) return null;
    try {
      const res = await fetch(`${this.apiUrl}/user/${userId}`);
      if (res.ok) {
        const data = await res.json();
        // Check for error response from backend or missing data
        if (data.error || Object.keys(data).length === 0) {
          console.warn("User profile fetch returned error or empty:", data);
          return null;
        }
        return data;
      }
    } catch (e) {
      console.error("Failed to fetch profile", e);
    }
    return null;
  }

  async saveCourse(course: SavedCourse): Promise<boolean> {
    // 1. Local Storage (Backup)
    const courses = JSON.parse(localStorage.getItem('courses') || '[]');
    courses.push(course);
    localStorage.setItem('courses', JSON.stringify(courses));

    // 2. Backend API
    try {
      const userId = localStorage.getItem('temp_user_id');
      if (userId) {
        await fetch(`${this.apiUrl}/user/courses`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ...course, userId })
        });
      }
      return true;
    } catch (e) {
      console.error("Failed to save course to server", e);
      return false;
    }
  }

  async getCourses(): Promise<SavedCourse[]> {
    const userId = localStorage.getItem('temp_user_id');
    const hasAccessToken = !!localStorage.getItem('access_token');

    // 게스트는 백엔드에서 가져오지 않음
    if (!userId || !hasAccessToken) {
      return [];
    }

    try {
      const res = await fetch(`${this.apiUrl}/journey/history/${userId}`);
      if (res.ok) {
        const serverCourses = await res.json();
        // Merge with local if needed, or just return server
        return serverCourses.length > 0 ? serverCourses : JSON.parse(localStorage.getItem('courses') || '[]');
      }
    } catch (e) {
      console.error("Failed to fetch courses", e);
    }
    return JSON.parse(localStorage.getItem('courses') || '[]');
  }

  async deleteCourse(id: string): Promise<void> {
    const courses = JSON.parse(localStorage.getItem('courses') || '[]');
    const filtered = courses.filter((c: any) => c.id !== id);
    localStorage.setItem('courses', JSON.stringify(filtered));
  }

  async getUserStatistics(): Promise<any> {
    const userId = localStorage.getItem('temp_user_id');
    if (!userId) return null;
    try {
      const res = await fetch(`${this.apiUrl}/user/${userId}/statistics`);
      if (res.ok) {
        return await res.json();
      }
    } catch (e) {
      console.error("Failed to fetch statistics", e);
    }
    return null;
  }

  async getAgentContext(): Promise<any> {
    const userId = localStorage.getItem('temp_user_id');
    if (!userId) return null;
    try {
      const res = await fetch(`${this.apiUrl}/user/${userId}/agent-context`);
      if (res.ok) {
        return await res.json();
      }
    } catch (e) {
      console.error("Failed to fetch agent context", e);
    }
    return null;
  }

  /**
   * 코스 수정 요청 (Refine Agent)
   * 전체 파이프라인 재실행 없이 2~3초 내 부분 수정
   */
  async refineCourse(message: string, courseIndex: number = 0): Promise<{
    success: boolean;
    message: string;
    courses?: any[];
    changeSummary?: string;
  }> {
    const userId = localStorage.getItem('temp_user_id');
    if (!userId) return { success: false, message: '로그인이 필요합니다.' };

    try {
      const res = await fetch(`${this.apiUrl}/chat/refine`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userId, message, courseIndex }),
      });

      if (res.ok) {
        return await res.json();
      }
      return { success: false, message: '서버 오류가 발생했습니다.' };
    } catch (e) {
      console.error('[GeminiService] Refine error:', e);
      return { success: false, message: '네트워크 오류가 발생했습니다.' };
    }
  }

  /**
   * 사용자 입력이 여행/코스 추천에 유효한 질문인지 검증합니다.
   */
  async validateInput(message: string): Promise<{
    isValid: boolean;
    message: string;
    suggestions?: string[];
  }> {
    try {
      const res = await fetch(`${this.apiUrl}/chat/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message }),
      });

      if (res.ok) {
        return await res.json();
      }
      // 서버 오류 시 일단 유효한 것으로 처리
      return { isValid: true, message: '' };
    } catch (e) {
      console.error('[GeminiService] Validate error:', e);
      return { isValid: true, message: '' };
    }
  }

  // [New] Ensure User Sync across screens
  async syncUser(): Promise<void> {
    await this.getUserProfile();
  }

  /**
   * 개인화 초대장 조회
   * 사용자 데이터 기반으로 생성된 맞춤 초대장을 가져옵니다.
   * 없거나 이미 본 경우 null 반환
   */
  async getPersonalizedInvitation(): Promise<any | null> {
    const userId = localStorage.getItem('temp_user_id');
    if (!userId || !localStorage.getItem('access_token')) return null;

    try {
      const res = await fetch(`${this.apiUrl}/invitation/personalized/${userId}`);
      if (!res.ok) return null;
      const data = await res.json();
      return data.invitation || null;
    } catch (e) {
      console.error('[GeminiService] Failed to fetch personalized invitation', e);
      return null;
    }
  }

  /**
   * 개인화 초대장 열람 처리
   * 사용자가 개인화 초대장을 확인했음을 기록합니다.
   */
  async markPersonalizedInvitationViewed(): Promise<void> {
    const userId = localStorage.getItem('temp_user_id');
    if (!userId) return;

    try {
      await fetch(`${this.apiUrl}/invitation/personalized/viewed/${userId}`, {
        method: 'PATCH',
      });
    } catch (e) {
      console.error('[GeminiService] Failed to mark personalized invitation viewed', e);
    }
  }
}
