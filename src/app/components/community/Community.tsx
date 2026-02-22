import React, { useState, useEffect } from 'react';
import { motion } from 'motion/react';
import { Heart, MessageSquare, Share2, Plus, ShieldAlert, X } from 'lucide-react';
import { Button } from '../ui/button';

interface CommunityProps {
  onClose: () => void;
}

const posts = [
  {
    id: 1,
    author: "Butterfly_warrior",
    tag: "Navigating Referrals",
    content: "Finally got my GP to order an ANA panel after showing them the SOAP note. The malar rash photo was what convinced them. Don't give up on getting the right tests!",
    likes: 47,
    comments: 14,
    time: "2h ago",
    avatarColor: "#7B61FF"
  },
  {
    id: 2,
    author: "CRP_tracker",
    tag: "Research",
    content: "New Rheumatology paper links sustained NLR elevation with earlier Lupus onset. Exactly the trend Aura flagged for me — sharing the DOI in the comments.",
    likes: 156,
    comments: 42,
    time: "5h ago",
    avatarColor: "#3ECFCF"
  },
  {
    id: 3,
    author: "Joint_journal",
    tag: "Success Story",
    content: "Got my Rheumatology appointment! The specialist said the clinical summary was the clearest patient-initiated referral she'd seen. Keep documenting your patterns.",
    likes: 89,
    comments: 12,
    time: "1d ago",
    avatarColor: "#F4A261"
  }
];

export const Community = ({ onClose }: CommunityProps) => {
  // Close on ESC
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 bg-[#0A0D14] overflow-y-auto">
      <div className="max-w-3xl mx-auto min-h-screen pb-20 relative">
        
        {/* Header */}
        <div className="sticky top-0 z-40 bg-[#0A0D14]/80 backdrop-blur-md border-b border-[#1A1D26] p-4 flex items-center justify-between">
          <h2 className="text-xl font-display font-medium text-white">Community</h2>
          <button onClick={onClose} className="p-2 hover:bg-[#1A1D26] rounded-full text-[#8A93B2] hover:text-white transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          
          {/* Welcome Card */}
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="p-6 rounded-2xl bg-[#13161F] border border-[#F4A261]/30 shadow-[0_0_20px_rgba(244,162,97,0.1)] relative overflow-hidden"
          >
            <div className="absolute top-0 right-0 w-32 h-32 bg-[#F4A261]/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />
            <h3 className="text-2xl font-display font-medium text-[#F4A261] mb-2">
              You've been matched to the Systemic Autoimmune Community.
            </h3>
            <p className="text-[#8A93B2]">
              Connect with others navigating similar inflammatory and autoimmune symptom patterns.
            </p>
          </motion.div>

          {/* Moderation Banner */}
          <div className="flex items-start gap-3 p-4 rounded-lg bg-[#3ECFCF]/10 border border-[#3ECFCF]/20 text-[#3ECFCF] text-sm">
            <ShieldAlert className="w-5 h-5 flex-shrink-0" />
            <p>
              This is a space for navigation, not diagnosis. Medical advice is auto-removed by our moderation bot.
            </p>
          </div>

          {/* Feed */}
          <div className="space-y-4">
            {posts.map((post, i) => (
              <motion.div
                key={post.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
                className="p-6 rounded-xl bg-[#13161F] border border-[#2A2E3B] hover:border-[#7B61FF]/30 transition-colors group"
              >
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    {/* Abstract Avatar */}
                    <div 
                      className="w-10 h-10 rounded-full flex items-center justify-center overflow-hidden"
                      style={{ background: `linear-gradient(135deg, ${post.avatarColor}20, ${post.avatarColor}40)` }}
                    >
                      <svg width="100%" height="100%" viewBox="0 0 40 40">
                         <circle cx="20" cy="20" r="8" fill={post.avatarColor} opacity="0.6" />
                         <circle cx="28" cy="12" r="4" fill={post.avatarColor} opacity="0.4" />
                         <circle cx="10" cy="28" r="6" fill={post.avatarColor} opacity="0.3" />
                      </svg>
                    </div>
                    <div>
                      <h4 className="font-medium text-[#F0F2F8]">{post.author}</h4>
                      <span className="text-xs text-[#8A93B2]">{post.time}</span>
                    </div>
                  </div>
                  <span className="text-xs px-2 py-1 rounded-full bg-[#1A1D26] border border-[#2A2E3B] text-[#8A93B2]">
                    {post.tag}
                  </span>
                </div>

                <p className="text-[#F0F2F8]/90 mb-4 leading-relaxed">
                  {post.content}
                </p>

                <div className="flex items-center gap-6 text-[#8A93B2] text-sm">
                  <button className="flex items-center gap-2 hover:text-[#E07070] transition-colors group/like">
                    <Heart className="w-4 h-4 group-hover/like:fill-current" />
                    {post.likes}
                  </button>
                  <button className="flex items-center gap-2 hover:text-[#3ECFCF] transition-colors">
                    <MessageSquare className="w-4 h-4" />
                    {post.comments}
                  </button>
                  <button className="flex items-center gap-2 hover:text-[#7B61FF] transition-colors ml-auto">
                    <Share2 className="w-4 h-4" />
                  </button>
                </div>
              </motion.div>
            ))}
          </div>
        </div>

        {/* Floating Action Button */}
        <motion.div 
          className="fixed bottom-8 right-8 z-50"
          whileHover={{ scale: 1.05 }}
        >
          <button className="flex items-center gap-0 overflow-hidden h-12 rounded-full bg-[#00B4D8] text-white shadow-lg hover:shadow-[0_0_20px_rgba(0,180,216,0.4)] transition-all group pr-4 pl-4 hover:pl-5">
             <Plus className="w-6 h-6 flex-shrink-0" />
             <span className="max-w-0 group-hover:max-w-xs transition-all duration-300 overflow-hidden whitespace-nowrap opacity-0 group-hover:opacity-100 group-hover:ml-2">
               Share Your Experience
             </span>
          </button>
        </motion.div>

      </div>
    </div>
  );
};
