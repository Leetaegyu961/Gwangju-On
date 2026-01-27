

import { CoursePoint, SavedCourse, Message, EvidenceCard } from "../types";

export class GeminiService {
  private apiUrl: string;

  constructor() {
    this.apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';
  }

  async processRequest(input: string, onStatusChange?: (status: Message['status']) => void): Promise<Message> {
    try {
      if (onStatusChange) onStatusChange('analyzing');

      // userId 가져오기
      const userId = localStorage.getItem('temp_user_id') || undefined;

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

  async saveCourse(courseData: any): Promise<boolean> {
    try {
      const resp = await fetch(`${this.apiUrl}/course/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(courseData),
      });
      return resp.ok;
    } catch (e) {
      console.error("Save Course Error:", e);
      return false;
    }
  }

  async getCourses(): Promise<any[]> {
    try {
      const userId = localStorage.getItem('temp_user_id');
      if (!userId) return [];

      const resp = await fetch(`${this.apiUrl}/user/saved-courses?userId=${userId}`);
      if (!resp.ok) return [];
      return await resp.json();
    } catch (e) {
      console.error("Get Courses Error:", e);
      return [];
    }
  }

  async deleteCourse(id: string): Promise<void> {
    // Backend API for deletion needs implementation if required
    console.log("Delete Course (Local Mock):", id);
  }
}
