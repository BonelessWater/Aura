import React, { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { toast, Toaster } from 'sonner';
import {
  Shield, Lock, Cloud, FileText, Download, Trash2,
  Eye, EyeOff, ToggleLeft, Users, X, AlertTriangle,
  ChevronRight, HardDrive, Fingerprint
} from 'lucide-react';
import { clsx } from 'clsx';
import { GenerativeAvatar } from '../components/layout/Navbar';
import { SkeletonRow } from '../components/shared/SkeletonBlock';

/* ---------- Types ---------- */
interface VaultDocument {
  id: string;
  name: string;
  type: 'pdf' | 'soap' | 'image';
  dateAdded: string;
  size: string;
}

/* ---------- Mock data ---------- */
const initialDocuments: VaultDocument[] = [
  { id: '1', name: 'lab_results_2026_jan.pdf', type: 'pdf', dateAdded: 'Jan 15, 2026', size: '2.4 MB' },
  { id: '2', name: 'SOAP_clinical_summary.pdf', type: 'soap', dateAdded: 'Jan 16, 2026', size: '180 KB' },
  { id: '3', name: 'blood_panel_dec_2025.pdf', type: 'pdf', dateAdded: 'Dec 22, 2025', size: '1.8 MB' },
  { id: '4', name: 'wearable_data_export.pdf', type: 'pdf', dateAdded: 'Dec 10, 2025', size: '4.1 MB' },
  { id: '5', name: 'SOAP_follow_up.pdf', type: 'soap', dateAdded: 'Nov 28, 2025', size: '210 KB' },
];

/* ---------- Sub-components ---------- */

const StorageToggle = ({
  isCloud,
  onToggle,
}: {
  isCloud: boolean;
  onToggle: () => void;
}) => (
  <div className="flex items-center gap-4 p-4 rounded-xl bg-[#0D0F16] border border-[#1A1D26]">
    <button
      onClick={() => isCloud && onToggle()}
      className={clsx(
        'flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all flex-1 justify-center',
        !isCloud
          ? 'bg-[#7B61FF]/15 border border-[#7B61FF]/40 text-[#7B61FF] shadow-[0_0_20px_rgba(123,97,255,0.1)]'
          : 'text-[#8A93B2] hover:text-white'
      )}
    >
      <HardDrive className="w-4 h-4" />
      Local Processing Only
    </button>

    <button
      onClick={() => !isCloud && onToggle()}
      className={clsx(
        'flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all flex-1 justify-center',
        isCloud
          ? 'bg-[#2563EB]/15 border border-[#2563EB]/40 text-[#2563EB] shadow-[0_0_20px_rgba(37,99,235,0.1)]'
          : 'text-[#8A93B2] hover:text-white'
      )}
    >
      <Cloud className="w-4 h-4" />
      Cloud Backup
    </button>
  </div>
);

const PrivacyToggleRow = ({
  label,
  enabled,
  onToggle,
}: {
  label: string;
  enabled: boolean;
  onToggle: () => void;
}) => (
  <div className="flex items-center justify-between py-3 px-1">
    <span className="text-sm text-[#F0F2F8]/80">{label}</span>
    <button
      onClick={onToggle}
      className={clsx(
        'relative w-11 h-6 rounded-full transition-colors duration-300',
        enabled ? 'bg-[#7B61FF]' : 'bg-[#2A2E3B]'
      )}
    >
      <motion.div
        className="absolute top-0.5 w-5 h-5 rounded-full bg-white shadow-md"
        animate={{ left: enabled ? 22 : 2 }}
        transition={{ type: 'spring', stiffness: 400, damping: 25 }}
      />
    </button>
  </div>
);

/* ---------- Main Component ---------- */
export const Vault = () => {
  const [documents, setDocuments] = useState<VaultDocument[]>(initialDocuments);
  const [isCloud, setIsCloud] = useState(false);
  const [showEncryptionModal, setShowEncryptionModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState<string | null>(null);
  const [deletingIds, setDeletingIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);

  // Privacy toggles
  const [shareConfidence, setShareConfidence] = useState(true);
  const [shareSymptoms, setShareSymptoms] = useState(true);
  const [shareDemographics, setShareDemographics] = useState(false);

  const [encPassword, setEncPassword] = useState('');
  const [encConfirm, setEncConfirm] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  const handleStorageToggle = () => {
    if (!isCloud) {
      // Switching TO cloud -> prompt encryption
      setShowEncryptionModal(true);
    } else {
      setIsCloud(false);
      toast.success('Switched to local processing only.');
    }
  };

  const handleEncryptionSetup = () => {
    if (encPassword.length < 8) {
      toast.error('Password must be at least 8 characters.');
      return;
    }
    if (encPassword !== encConfirm) {
      toast.error('Passwords do not match.');
      return;
    }
    setIsCloud(true);
    setShowEncryptionModal(false);
    setEncPassword('');
    setEncConfirm('');
    toast.success('Cloud backup enabled with end-to-end encryption.');
  };

  const handleDelete = useCallback((id: string) => {
    setDeletingIds((prev) => new Set(prev).add(id));
    setShowDeleteModal(null);

    // Animate out, then remove
    setTimeout(() => {
      setDocuments((prev) => prev.filter((d) => d.id !== id));
      setDeletingIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
      toast.success('File permanently deleted.');
    }, 350);
  }, []);

  const handleRevokeAll = () => {
    setShareConfidence(false);
    setShareSymptoms(false);
    setShareDemographics(false);
    toast('Community access revoked. Your posts have been removed.', {
      icon: <Shield className="w-4 h-4 text-[#E07070]" />,
    });
  };

  const docToDelete = documents.find((d) => d.id === showDeleteModal);

  return (
    <>
      <Toaster
        position="bottom-right"
        toastOptions={{
          style: {
            background: '#13161F',
            border: '1px solid #2A2E3B',
            color: '#F0F2F8',
          },
        }}
      />

      <div
        className="min-h-screen pt-20 pb-20 px-4 md:px-8"
        style={{
          background: 'linear-gradient(180deg, #05070A 0%, #0A0D14 40%)',
        }}
      >
        <div className="max-w-3xl mx-auto space-y-8">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center gap-5 mb-2"
          >
            <div className="ring-2 ring-[#7B61FF]/30 ring-offset-4 ring-offset-[#05070A] rounded-full">
              <GenerativeAvatar seed="aura_user_42" size={56} />
            </div>
            <div>
              <h1 className="text-[28px] font-display font-semibold text-white">
                Your Medical Vault
              </h1>
              <p className="text-sm text-[#8A93B2] mt-0.5">
                Private. Encrypted. Under your control.
              </p>
            </div>
          </motion.div>

          {/* Data Management */}
          <motion.section
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="bg-[#0F1119] border border-[#1A1D26] rounded-2xl p-6 space-y-5"
          >
            <div className="flex items-center gap-2 mb-1">
              <Lock className="w-4 h-4 text-[#7B61FF]" />
              <h2 className="text-lg font-display font-medium text-white">
                Data Storage
              </h2>
            </div>

            <StorageToggle isCloud={isCloud} onToggle={handleStorageToggle} />

            <div className="flex items-start gap-3 p-3 rounded-lg bg-[#7B61FF]/[0.04] border border-[#7B61FF]/10 text-xs text-[#8A93B2] leading-relaxed">
              <Fingerprint className="w-4 h-4 text-[#7B61FF] flex-shrink-0 mt-0.5" />
              {isCloud ? (
                <span>
                  Your data is encrypted end-to-end before leaving this device. Only you hold the decryption key.
                </span>
              ) : (
                <span>
                  Your data never leaves this device. If you clear your browser cache, your history is lost.
                </span>
              )}
            </div>
          </motion.section>

          {/* Document Archive */}
          <motion.section
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="bg-[#0F1119] border border-[#1A1D26] rounded-2xl p-6 space-y-4"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-[#2563EB]" />
                <h2 className="text-lg font-display font-medium text-white">
                  Document Archive
                </h2>
              </div>
              <span className="text-xs text-[#8A93B2] font-mono">
                {documents.length} files
              </span>
            </div>

            {loading ? (
              <div className="space-y-3">
                {Array.from({ length: 3 }).map((_, i) => (
                  <SkeletonRow key={i} />
                ))}
              </div>
            ) : (
              <div className="space-y-2">
                <AnimatePresence>
                  {documents.map((doc) => {
                    const isDeleting = deletingIds.has(doc.id);
                    return (
                      <motion.div
                        key={doc.id}
                        layout
                        initial={{ opacity: 1, height: 'auto' }}
                        animate={{
                          opacity: isDeleting ? 0 : 1,
                          height: isDeleting ? 0 : 'auto',
                        }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.3 }}
                        className="overflow-hidden"
                      >
                        <div className="flex items-center gap-4 p-4 rounded-lg bg-[#0D0F16] border border-[#1A1D26] hover:border-[#2A2E3B] transition-colors group">
                          {/* Icon */}
                          <div
                            className={clsx(
                              'w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0',
                              doc.type === 'soap'
                                ? 'bg-[#F4A261]/10'
                                : 'bg-[#7B61FF]/10'
                            )}
                          >
                            <FileText
                              className={clsx(
                                'w-5 h-5',
                                doc.type === 'soap'
                                  ? 'text-[#F4A261]'
                                  : 'text-[#7B61FF]'
                              )}
                            />
                          </div>

                          {/* Info */}
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-[#F0F2F8] truncate">
                              {doc.name}
                            </p>
                            <p className="text-xs text-[#8A93B2] mt-0.5 font-mono">
                              {doc.dateAdded} &middot; {doc.size}
                            </p>
                          </div>

                          {/* Actions */}
                          <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                            <button
                              className="p-2 rounded-lg hover:bg-[#1A1D26] text-[#8A93B2] hover:text-[#2563EB] transition-colors"
                              title="Download"
                            >
                              <Download className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => setShowDeleteModal(doc.id)}
                              className="p-2 rounded-lg hover:bg-[#E07070]/10 text-[#8A93B2] hover:text-[#E07070] transition-colors"
                              title="Delete"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      </motion.div>
                    );
                  })}
                </AnimatePresence>

                {documents.length === 0 && (
                  <div className="py-12 text-center text-[#8A93B2] text-sm">
                    No documents in your vault.
                  </div>
                )}
              </div>
            )}
          </motion.section>

          {/* Privacy Controls */}
          <motion.section
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="bg-[#0F1119] border border-[#1A1D26] rounded-2xl p-6 space-y-4"
          >
            <div className="flex items-center gap-2">
              <Shield className="w-4 h-4 text-[#F4A261]" />
              <h2 className="text-lg font-display font-medium text-white">
                Privacy Controls
              </h2>
            </div>
            <p className="text-xs text-[#8A93B2]">
              Manage what data is shared with the Community Forum.
            </p>

            <div className="divide-y divide-[#1A1D26]">
              <PrivacyToggleRow
                label="Share Category Confidence Score"
                enabled={shareConfidence}
                onToggle={() => setShareConfidence(!shareConfidence)}
              />
              <PrivacyToggleRow
                label="Share General Symptoms"
                enabled={shareSymptoms}
                onToggle={() => setShareSymptoms(!shareSymptoms)}
              />
              <PrivacyToggleRow
                label="Share Age / Demographics"
                enabled={shareDemographics}
                onToggle={() => setShareDemographics(!shareDemographics)}
              />
            </div>

            <div className="pt-2">
              <button
                onClick={handleRevokeAll}
                className="w-full py-3 rounded-lg border border-[#E07070]/30 text-[#E07070] text-sm font-medium hover:bg-[#E07070]/10 transition-colors flex items-center justify-center gap-2"
              >
                <Users className="w-4 h-4" />
                Revoke All Community Access
              </button>
            </div>
          </motion.section>
        </div>
      </div>

      {/* ---- Delete Confirmation Modal ---- */}
      <AnimatePresence>
        {showDeleteModal && docToDelete && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[200] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
            onClick={() => setShowDeleteModal(null)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-md bg-[#13161F] border border-[#2A2E3B] rounded-2xl p-6 shadow-2xl"
            >
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-full bg-[#E07070]/10 flex items-center justify-center">
                  <AlertTriangle className="w-5 h-5 text-[#E07070]" />
                </div>
                <h3 className="text-lg font-display font-medium text-white">
                  Delete File
                </h3>
              </div>

              <p className="text-sm text-[#8A93B2] mb-2">
                Are you sure you want to permanently delete:
              </p>
              <p className="text-sm text-[#F0F2F8] font-mono bg-[#0D0F16] p-3 rounded-lg border border-[#1A1D26] mb-6">
                {docToDelete.name}
              </p>
              <p className="text-xs text-[#8A93B2] mb-6">
                This action cannot be undone.
              </p>

              <div className="flex gap-3">
                <button
                  onClick={() => setShowDeleteModal(null)}
                  className="flex-1 py-2.5 rounded-lg border border-[#2A2E3B] text-[#8A93B2] text-sm hover:bg-[#1A1D26] transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={() => handleDelete(docToDelete.id)}
                  className="flex-1 py-2.5 rounded-lg bg-[#E07070] text-white text-sm font-medium hover:bg-[#d05050] transition-colors"
                >
                  Permanently Delete
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ---- Encryption Setup Modal ---- */}
      <AnimatePresence>
        {showEncryptionModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[200] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
            onClick={() => setShowEncryptionModal(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-md bg-[#13161F] border border-[#2A2E3B] rounded-2xl p-6 shadow-2xl"
            >
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-[#2563EB]/10 flex items-center justify-center">
                    <Lock className="w-5 h-5 text-[#2563EB]" />
                  </div>
                  <h3 className="text-lg font-display font-medium text-white">
                    Set Encryption Password
                  </h3>
                </div>
                <button
                  onClick={() => setShowEncryptionModal(false)}
                  className="p-1 hover:bg-[#1A1D26] rounded-full text-[#8A93B2]"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <p className="text-sm text-[#8A93B2] mb-5 leading-relaxed">
                Your data will be encrypted end-to-end before leaving this device. Choose a strong password you'll remember — there is no recovery option.
              </p>

              <div className="space-y-4">
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={encPassword}
                    onChange={(e) => setEncPassword(e.target.value)}
                    placeholder="Password (min 8 characters)"
                    className="w-full bg-[#0D0F16] border border-[#2A2E3B] rounded-lg px-4 py-3 text-sm text-[#F0F2F8] placeholder:text-[#8A93B2]/40 focus:border-[#2563EB] focus:outline-none"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-[#8A93B2] hover:text-white"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>

                <input
                  type={showPassword ? 'text' : 'password'}
                  value={encConfirm}
                  onChange={(e) => setEncConfirm(e.target.value)}
                  placeholder="Confirm password"
                  className="w-full bg-[#0D0F16] border border-[#2A2E3B] rounded-lg px-4 py-3 text-sm text-[#F0F2F8] placeholder:text-[#8A93B2]/40 focus:border-[#2563EB] focus:outline-none"
                />
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowEncryptionModal(false)}
                  className="flex-1 py-2.5 rounded-lg border border-[#2A2E3B] text-[#8A93B2] text-sm hover:bg-[#1A1D26] transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleEncryptionSetup}
                  className="flex-1 py-2.5 rounded-lg bg-[#2563EB] text-[#0A0D14] text-sm font-medium hover:bg-[#1E40AF] transition-colors"
                >
                  Enable Cloud Backup
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};