
import { GoogleGenerativeAI } from "@google/generative-ai";
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

  async saveCourse(course: SavedCourse): Promise<boolean> {
    const courses = JSON.parse(localStorage.getItem('courses') || '[]');
    courses.push(course);
    localStorage.setItem('courses', JSON.stringify(courses));
    return true;
  }

  async getCourses(): Promise<SavedCourse[]> {
    return JSON.parse(localStorage.getItem('courses') || '[]');
  }

  async deleteCourse(id: string): Promise<void> {
    const courses = JSON.parse(localStorage.getItem('courses') || '[]');
    const filtered = courses.filter((c: any) => c.id !== id);
    localStorage.setItem('courses', JSON.stringify(filtered));
  }
}
