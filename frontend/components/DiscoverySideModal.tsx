
"use client";

import React from 'react';
import { X, Hash, Sparkles } from 'lucide-react';

/**
 * [Prompt 6: Discovery Screen / Drawer Refinement]
 */
export const DiscoverySideModal = ({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) => {
  const categories = [
    { title: '맛집', sub: 'Restaurants', img: 'https://images.unsplash.com/photo-1514362545857-3bc16c4c7d1b?w=400' },
    { title: '카페', sub: 'Cafes', img: 'https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=400' },
    { title: '추천 코스', sub: 'Courses', img: 'https://images.unsplash.com/photo-1526778548025-fa2f459cd5c1?w=400' },
    { title: '쇼핑', sub: 'Shopping', img: 'https://images.unsplash.com/photo-1534452286882-6fc6910939b0?w=400' },
  ];

  const keywords = ['#힐링', '#로컬맛집', '#인생샷', '#조용한', '#예술적', '#가족과함께', '#반려동물'];

  return (
    <>
      <div
        className={`fixed inset-0 bg-black/60 backdrop-blur-md z-[300] transition-opacity duration-500 ${isOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'}`}
        onClick={onClose}
      />
      <div
        className={`fixed top-0 left-0 h-full w-[85%] bg-white z-[301] shadow-2xl transition-transform duration-700 cubic-bezier(0.32, 0.72, 0, 1) transform ${isOpen ? 'translate-x-0' : '-translate-x-full'} rounded-r-[3.5rem] overflow-hidden`}
      >
        <div className="p-10 pt-20 h-full flex flex-col">
          <div className="flex justify-between items-center mb-12">
            <div>
              <p className="text-[10px] font-black text-[#0066FF] uppercase tracking-[0.3em] mb-1">Discovery</p>
              <h2 className="text-3xl font-black text-gray-900 tracking-tighter italic">카테고리 탐색</h2>
            </div>
            <button onClick={onClose} className="p-3 bg-gray-50 rounded-2xl text-gray-300 hover:text-gray-900 transition-all hover:rotate-90">
              <X size={20} />
            </button>
          </div>

          <div className="grid grid-cols-2 gap-4 mb-14">
            {categories.map(c => (
              <div key={c.title} className="group relative h-48 rounded-[2.5rem] overflow-hidden shadow-xl cursor-pointer active:scale-95 transition-all">
                <img src={c.img} className="w-full h-full object-cover transition-transform duration-[1.5s] group-hover:scale-125" alt={c.title} />
                <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/20 to-transparent flex flex-col justify-end p-6">
                  <span className="text-[9px] font-black text-blue-400 uppercase tracking-widest mb-1.5 opacity-80">{c.sub}</span>
                  <h3 className="text-base font-black text-white tracking-tight">{c.title}</h3>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-auto pb-6">
            <div className="flex items-center gap-3 mb-8">
              <div className="w-8 h-8 bg-blue-50 rounded-xl flex items-center justify-center">
                <Sparkles size={16} className="text-[#0066FF]" />
              </div>
              <h3 className="text-sm font-black text-gray-900 uppercase tracking-wider">나의 취향 키워드</h3>
            </div>
            <div className="flex flex-wrap gap-2.5">
              {keywords.map(kw => (
                <span
                  key={kw}
                  className="px-5 py-3 bg-gray-50 text-gray-400 text-[11px] font-black rounded-2xl border border-gray-100 hover:border-blue-200 hover:text-[#0066FF] hover:bg-blue-50 transition-all cursor-pointer shadow-sm hover:shadow-md"
                >
                  {kw}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  );
};
