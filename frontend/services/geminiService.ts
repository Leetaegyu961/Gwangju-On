

import { CoursePoint, SavedCourse, Message, EvidenceCard, CourseInfo } from "../types";

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
    if (!userId) return JSON.parse(localStorage.getItem('courses') || '[]');

    try {
      const res = await fetch(`${this.apiUrl}/user/${userId}/courses`);
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
}