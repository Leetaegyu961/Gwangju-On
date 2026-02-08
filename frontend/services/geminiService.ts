
import { CoursePoint, SavedCourse, Message, EvidenceCard, CourseInfo } from "../types";

export class GeminiService {
  private apiUrl: string;

  constructor() {
    this.apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';
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

  // [New] Ensure User Sync across screens
  async syncUser(): Promise<void> {
    await this.getUserProfile();
  }
}
