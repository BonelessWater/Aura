import React, { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { toast, Toaster } from 'sonner';
import {
  Shield, Lock, Cloud, FileText, Download, Trash2,
  Eye, EyeOff, Users, X, AlertTriangle,
  HardDrive, Fingerprint, User, Bell, MapPin,
  ChevronRight, ChevronLeft, LogOut, Moon, Globe, Mail, Smartphone
} from 'lucide-react';
import { clsx } from 'clsx';
import { useNavigate } from 'react-router';
import { GenerativeAvatar } from '../components/layout/Navbar';

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

/* ---------- Nav Items ---------- */
const navSections = [
  { id: 'profile', label: 'Profile', icon: User },
  { id: 'storage', label: 'Data Storage', icon: Lock },
  { id: 'documents', label: 'Documents', icon: FileText },
  { id: 'privacy', label: 'Privacy', icon: Shield },
  { id: 'notifications', label: 'Notifications', icon: Bell },
  { id: 'account', label: 'Account', icon: LogOut },
];

/* ---------- Toggle row ---------- */
const ToggleRow = ({
  label,
  description,
  enabled,
  onToggle,
}: {
  label: string;
  description?: string;
  enabled: boolean;
  onToggle: () => void;
}) => (
  <div className="flex items-center justify-between py-3.5 group">
    <div className="pr-4">
      <p className="text-sm text-[#F0F2F8]">{label}</p>
      {description && <p className="text-[11px] text-[#8A93B2] mt-0.5">{description}</p>}
    </div>
    <button
      onClick={onToggle}
      className={clsx(
        'relative w-11 h-6 rounded-full transition-colors duration-300 flex-shrink-0',
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

/* ---------- Section wrapper ---------- */
const SettingsSection = ({
  id,
  title,
  icon: Icon,
  children,
  delay = 0,
}: {
  id: string;
  title: string;
  icon: typeof User;
  children: React.ReactNode;
  delay?: number;
}) => (
  <motion.section
    id={id}
    initial={{ opacity: 0, y: 16 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ delay }}
    className="bg-[#0F1119] border border-[#1A1D26] rounded-2xl overflow-hidden"
  >
    <div className="px-6 py-4 border-b border-[#1A1D26] flex items-center gap-2.5">
      <Icon className="w-4 h-4 text-[#7B61FF]" />
      <h2 className="text-[15px] font-display font-semibold text-[#F0F2F8]">{title}</h2>
    </div>
    <div className="px-6 py-5">{children}</div>
  </motion.section>
);

/* ---------- Main Component ---------- */
export const Vault = () => {
  const navigate = useNavigate();
  const [documents, setDocuments] = useState<VaultDocument[]>(initialDocuments);
  const [isCloud, setIsCloud] = useState(false);
  const [showEncryptionModal, setShowEncryptionModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState<string | null>(null);
  const [deletingIds, setDeletingIds] = useState<Set<string>>(new Set());

  // Privacy
  const [shareConfidence, setShareConfidence] = useState(true);
  const [shareSymptoms, setShareSymptoms] = useState(true);
  const [shareDemographics, setShareDemographics] = useState(false);

  // Notifications
  const [notifyResults, setNotifyResults] = useState(true);
  const [notifyCommunity, setNotifyCommunity] = useState(true);
  const [notifyResearch, setNotifyResearch] = useState(false);

  // Encryption modal
  const [encPassword, setEncPassword] = useState('');
  const [encConfirm, setEncConfirm] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  // Active nav
  const [activeNav, setActiveNav] = useState('profile');

  const handleStorageToggle = () => {
    if (!isCloud) {
      setShowEncryptionModal(true);
    } else {
      setIsCloud(false);
      toast.success('Switched to local processing only.');
    }
  };

  const handleEncryptionSetup = () => {
    if (encPassword.length < 8) { toast.error('Password must be at least 8 characters.'); return; }
    if (encPassword !== encConfirm) { toast.error('Passwords do not match.'); return; }
    setIsCloud(true);
    setShowEncryptionModal(false);
    setEncPassword('');
    setEncConfirm('');
    toast.success('Cloud backup enabled with end-to-end encryption.');
  };

  const handleDelete = useCallback((id: string) => {
    setDeletingIds((prev) => new Set(prev).add(id));
    setShowDeleteModal(null);
    setTimeout(() => {
      setDocuments((prev) => prev.filter((d) => d.id !== id));
      setDeletingIds((prev) => { const next = new Set(prev); next.delete(id); return next; });
      toast.success('File permanently deleted.');
    }, 350);
  }, []);

  const handleRevokeAll = () => {
    setShareConfidence(false);
    setShareSymptoms(false);
    setShareDemographics(false);
    toast('Community access revoked.', { icon: <Shield className="w-4 h-4 text-[#E07070]" /> });
  };

  const scrollToSection = (id: string) => {
    setActiveNav(id);
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const docToDelete = documents.find((d) => d.id === showDeleteModal);

  const totalSize = '8.7 MB';

  return (
    <>
      <Toaster
        position="bottom-right"
        toastOptions={{ style: { background: '#13161F', border: '1px solid #2A2E3B', color: '#F0F2F8' } }}
      />

      <div
        className="min-h-screen pt-20 pb-20 px-4 md:px-8"
        style={{ background: 'linear-gradient(180deg, #05070A 0%, #0A0D14 40%)' }}
      >
        <div className="max-w-5xl mx-auto flex gap-8">

          {/* ── Left Navigation ── */}
          <nav className="hidden md:block w-[220px] flex-shrink-0 sticky top-24 self-start">
            {/* User card */}
            <div className="mb-6 p-4 rounded-xl bg-[#0F1119] border border-[#1A1D26]">
              <div className="flex items-center gap-3 mb-3">
                <div className="ring-2 ring-[#7B61FF]/30 ring-offset-2 ring-offset-[#0F1119] rounded-full">
                  <GenerativeAvatar seed="aura_user_42" size={40} />
                </div>
                <div>
                  <p className="text-sm font-medium text-[#F0F2F8]">Aura User</p>
                  <p className="text-[10px] text-[#8A93B2] font-mono">Atlanta, GA</p>
                </div>
              </div>
              <div className="flex items-center gap-2 text-[10px] font-mono text-[#8A93B2]">
                <Lock className="w-3 h-3 text-[#52D0A0]" />
                <span className="text-[#52D0A0]">Data encrypted</span>
                <span>· {totalSize} stored</span>
              </div>
            </div>

            {/* Nav links */}
            <div className="space-y-0.5">
              {navSections.map(s => {
                const Icon = s.icon;
                const isActive = activeNav === s.id;
                return (
                  <button
                    key={s.id}
                    onClick={() => scrollToSection(s.id)}
                    className={clsx(
                      'w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-left text-sm transition-all',
                      isActive
                        ? 'bg-[#7B61FF]/10 text-[#F0F2F8] font-medium'
                        : 'text-[#8A93B2] hover:bg-[#1A1D26] hover:text-[#C0C7DC]'
                    )}
                  >
                    <Icon className={clsx('w-4 h-4', isActive && 'text-[#7B61FF]')} />
                    {s.label}
                  </button>
                );
              })}
            </div>
          </nav>

          {/* ── Main Content ── */}
          <div className="flex-1 space-y-6 min-w-0">

            {/* Page header */}
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <button
                onClick={() => navigate('/dashboard')}
                className="flex items-center gap-1.5 text-[#8A93B2] hover:text-[#F0F2F8] transition-colors mb-4 text-sm font-medium"
              >
                <ChevronLeft className="w-4 h-4" /> Back to Dashboard
              </button>
              <h1 className="text-2xl font-display font-semibold text-[#F0F2F8]">Settings & Data Vault</h1>
              <p className="text-sm text-[#8A93B2] mt-1">Manage your profile, data, privacy, and preferences.</p>
            </motion.div>

            {/* ═══ PROFILE ═══ */}
            <SettingsSection id="profile" title="Profile" icon={User} delay={0.05}>
              <div className="flex items-start gap-5 mb-5">
                <div className="ring-2 ring-[#7B61FF]/30 ring-offset-4 ring-offset-[#0F1119] rounded-full flex-shrink-0">
                  <GenerativeAvatar seed="aura_user_42" size={64} />
                </div>
                <div className="flex-1 space-y-3">
                  <div>
                    <label className="text-[10px] font-mono uppercase tracking-widest text-[#8A93B2] mb-1 block">Display Name</label>
                    <input
                      type="text" defaultValue="Aura User"
                      className="w-full bg-[#0D0F16] border border-[#2A2E3B] rounded-lg px-3 py-2.5 text-sm text-[#F0F2F8] focus:border-[#7B61FF]/40 focus:outline-none transition-colors"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-[10px] font-mono uppercase tracking-widest text-[#8A93B2] mb-1 block">Location</label>
                      <div className="flex items-center gap-2 bg-[#0D0F16] border border-[#2A2E3B] rounded-lg px-3 py-2.5">
                        <MapPin className="w-3.5 h-3.5 text-[#8A93B2]" />
                        <input
                          type="text" defaultValue="Atlanta, GA"
                          className="bg-transparent text-sm text-[#F0F2F8] focus:outline-none w-full"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="text-[10px] font-mono uppercase tracking-widest text-[#8A93B2] mb-1 block">Email</label>
                      <div className="flex items-center gap-2 bg-[#0D0F16] border border-[#2A2E3B] rounded-lg px-3 py-2.5">
                        <Mail className="w-3.5 h-3.5 text-[#8A93B2]" />
                        <input
                          type="email" defaultValue="user@example.com"
                          className="bg-transparent text-sm text-[#F0F2F8] focus:outline-none w-full"
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <div className="flex justify-end">
                <button className="px-5 py-2 rounded-lg text-sm font-medium bg-[#7B61FF]/10 text-[#7B61FF] border border-[#7B61FF]/15 hover:bg-[#7B61FF]/20 transition-all">
                  Save Changes
                </button>
              </div>
            </SettingsSection>

            {/* ═══ DATA STORAGE ═══ */}
            <SettingsSection id="storage" title="Data Storage" icon={Lock} delay={0.1}>
              <div className="flex items-center gap-4 p-4 rounded-xl bg-[#0D0F16] border border-[#1A1D26] mb-4">
                <button
                  onClick={() => isCloud && handleStorageToggle()}
                  className={clsx(
                    'flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all flex-1 justify-center',
                    !isCloud
                      ? 'bg-[#7B61FF]/15 border border-[#7B61FF]/40 text-[#7B61FF]'
                      : 'text-[#8A93B2] hover:text-white'
                  )}
                >
                  <HardDrive className="w-4 h-4" /> Local Only
                </button>
                <button
                  onClick={() => !isCloud && handleStorageToggle()}
                  className={clsx(
                    'flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all flex-1 justify-center',
                    isCloud
                      ? 'bg-[#2563EB]/15 border border-[#2563EB]/40 text-[#2563EB]'
                      : 'text-[#8A93B2] hover:text-white'
                  )}
                >
                  <Cloud className="w-4 h-4" /> Cloud Backup
                </button>
              </div>

              <div className="flex items-start gap-3 p-3 rounded-lg bg-[#7B61FF]/[0.04] border border-[#7B61FF]/10 text-xs text-[#8A93B2] leading-relaxed">
                <Fingerprint className="w-4 h-4 text-[#7B61FF] flex-shrink-0 mt-0.5" />
                {isCloud ? (
                  <span>Your data is encrypted end-to-end before leaving this device. Only you hold the decryption key.</span>
                ) : (
                  <span>Your data never leaves this device. If you clear your browser cache, your data will be lost.</span>
                )}
              </div>

              {/* Storage usage bar */}
              <div className="mt-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs text-[#8A93B2]">Storage used</span>
                  <span className="text-xs font-mono text-[#C0C7DC]">{totalSize} / 50 MB</span>
                </div>
                <div className="h-1.5 bg-[#1A1D26] rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: '17%' }}
                    transition={{ delay: 0.3, duration: 0.8, ease: 'easeOut' }}
                    className="h-full rounded-full bg-gradient-to-r from-[#7B61FF] to-[#2563EB]"
                  />
                </div>
              </div>
            </SettingsSection>

            {/* ═══ DOCUMENTS ═══ */}
            <SettingsSection id="documents" title="Documents" icon={FileText} delay={0.15}>
              <div className="flex items-center justify-between mb-4">
                <p className="text-xs text-[#8A93B2]">{documents.length} files in your vault</p>
                <button className="text-xs text-[#7B61FF] hover:text-[#9B85FF] transition-colors flex items-center gap-1">
                  <Download className="w-3 h-3" /> Download All
                </button>
              </div>

              <div className="space-y-2">
                <AnimatePresence>
                  {documents.map((doc) => {
                    const isDeleting = deletingIds.has(doc.id);
                    return (
                      <motion.div
                        key={doc.id}
                        layout
                        initial={{ opacity: 1, height: 'auto' }}
                        animate={{ opacity: isDeleting ? 0 : 1, height: isDeleting ? 0 : 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.3 }}
                        className="overflow-hidden"
                      >
                        <div className="flex items-center gap-4 p-3.5 rounded-lg bg-[#0D0F16] border border-[#1A1D26] hover:border-[#2A2E3B] transition-colors group">
                          <div className={clsx(
                            'w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0',
                            doc.type === 'soap' ? 'bg-[#F4A261]/10' : 'bg-[#7B61FF]/10'
                          )}>
                            <FileText className={clsx('w-4 h-4', doc.type === 'soap' ? 'text-[#F4A261]' : 'text-[#7B61FF]')} />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-[#F0F2F8] truncate">{doc.name}</p>
                            <p className="text-[11px] text-[#8A93B2] mt-0.5 font-mono">{doc.dateAdded} · {doc.size}</p>
                          </div>
                          <div className="flex items-center gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
                            <button className="p-2 rounded-lg hover:bg-[#1A1D26] text-[#8A93B2] hover:text-[#2563EB] transition-colors" title="Download">
                              <Download className="w-3.5 h-3.5" />
                            </button>
                            <button onClick={() => setShowDeleteModal(doc.id)} className="p-2 rounded-lg hover:bg-[#E07070]/10 text-[#8A93B2] hover:text-[#E07070] transition-colors" title="Delete">
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </div>
                      </motion.div>
                    );
                  })}
                </AnimatePresence>

                {documents.length === 0 && (
                  <div className="py-10 text-center text-[#8A93B2] text-sm">No documents in your vault.</div>
                )}
              </div>
            </SettingsSection>

            {/* ═══ PRIVACY ═══ */}
            <SettingsSection id="privacy" title="Privacy" icon={Shield} delay={0.2}>
              <p className="text-xs text-[#8A93B2] mb-3">Control what data is visible in Community Forums.</p>

              <div className="divide-y divide-[#1A1D26]">
                <ToggleRow
                  label="Share Category Confidence Score"
                  description="Other members can see your pattern match percentage"
                  enabled={shareConfidence}
                  onToggle={() => setShareConfidence(!shareConfidence)}
                />
                <ToggleRow
                  label="Share General Symptoms"
                  description="Visible in community matching and forum suggestions"
                  enabled={shareSymptoms}
                  onToggle={() => setShareSymptoms(!shareSymptoms)}
                />
                <ToggleRow
                  label="Share Age & Demographics"
                  description="Used for research aggregation only — never shown publicly"
                  enabled={shareDemographics}
                  onToggle={() => setShareDemographics(!shareDemographics)}
                />
              </div>

              <div className="pt-4">
                <button
                  onClick={handleRevokeAll}
                  className="w-full py-2.5 rounded-lg border border-[#E07070]/20 text-[#E07070] text-sm font-medium hover:bg-[#E07070]/5 transition-colors flex items-center justify-center gap-2"
                >
                  <Users className="w-4 h-4" /> Revoke All Community Access
                </button>
              </div>
            </SettingsSection>

            {/* ═══ NOTIFICATIONS ═══ */}
            <SettingsSection id="notifications" title="Notifications" icon={Bell} delay={0.25}>
              <div className="divide-y divide-[#1A1D26]">
                <ToggleRow
                  label="Analysis Results"
                  description="Get notified when your results are ready"
                  enabled={notifyResults}
                  onToggle={() => setNotifyResults(!notifyResults)}
                />
                <ToggleRow
                  label="Community Replies"
                  description="Someone replied to your post or comment"
                  enabled={notifyCommunity}
                  onToggle={() => setNotifyCommunity(!notifyCommunity)}
                />
                <ToggleRow
                  label="Research Updates"
                  description="New studies matching your profile are published"
                  enabled={notifyResearch}
                  onToggle={() => setNotifyResearch(!notifyResearch)}
                />
              </div>
            </SettingsSection>

            {/* ═══ ACCOUNT ═══ */}
            <SettingsSection id="account" title="Account" icon={LogOut} delay={0.3}>
              <div className="space-y-3">
                <button className="w-full flex items-center justify-between p-3.5 rounded-lg bg-[#0D0F16] border border-[#1A1D26] hover:border-[#2A2E3B] transition-colors group">
                  <div className="flex items-center gap-3">
                    <Download className="w-4 h-4 text-[#8A93B2] group-hover:text-[#2563EB] transition-colors" />
                    <div className="text-left">
                      <p className="text-sm text-[#F0F2F8]">Export All Data</p>
                      <p className="text-[11px] text-[#8A93B2]">Download everything as a ZIP archive</p>
                    </div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-[#8A93B2]" />
                </button>

                <button className="w-full flex items-center justify-between p-3.5 rounded-lg bg-[#0D0F16] border border-[#1A1D26] hover:border-[#E07070]/20 transition-colors group">
                  <div className="flex items-center gap-3">
                    <Trash2 className="w-4 h-4 text-[#8A93B2] group-hover:text-[#E07070] transition-colors" />
                    <div className="text-left">
                      <p className="text-sm text-[#F0F2F8]">Delete Account</p>
                      <p className="text-[11px] text-[#8A93B2]">Permanently remove all data — cannot be undone</p>
                    </div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-[#8A93B2]" />
                </button>

                <button className="w-full flex items-center justify-between p-3.5 rounded-lg bg-[#0D0F16] border border-[#1A1D26] hover:border-[#2A2E3B] transition-colors group">
                  <div className="flex items-center gap-3">
                    <LogOut className="w-4 h-4 text-[#8A93B2] group-hover:text-[#F4A261] transition-colors" />
                    <div className="text-left">
                      <p className="text-sm text-[#F0F2F8]">Sign Out</p>
                      <p className="text-[11px] text-[#8A93B2]">Your data stays encrypted on this device</p>
                    </div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-[#8A93B2]" />
                </button>
              </div>
            </SettingsSection>

          </div>
        </div>
      </div>

      {/* ──── Delete Confirmation Modal ──── */}
      <AnimatePresence>
        {showDeleteModal && docToDelete && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-[200] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
            onClick={() => setShowDeleteModal(null)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.95, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-md bg-[#13161F] border border-[#2A2E3B] rounded-2xl p-6 shadow-2xl"
            >
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-full bg-[#E07070]/10 flex items-center justify-center">
                  <AlertTriangle className="w-5 h-5 text-[#E07070]" />
                </div>
                <h3 className="text-lg font-display font-medium text-white">Delete File</h3>
              </div>
              <p className="text-sm text-[#8A93B2] mb-2">Are you sure you want to permanently delete:</p>
              <p className="text-sm text-[#F0F2F8] font-mono bg-[#0D0F16] p-3 rounded-lg border border-[#1A1D26] mb-6">{docToDelete.name}</p>
              <p className="text-xs text-[#8A93B2] mb-6">This action cannot be undone.</p>
              <div className="flex gap-3">
                <button onClick={() => setShowDeleteModal(null)} className="flex-1 py-2.5 rounded-lg border border-[#2A2E3B] text-[#8A93B2] text-sm hover:bg-[#1A1D26] transition-colors">Cancel</button>
                <button onClick={() => handleDelete(docToDelete.id)} className="flex-1 py-2.5 rounded-lg bg-[#E07070] text-white text-sm font-medium hover:bg-[#d05050] transition-colors">Permanently Delete</button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ──── Encryption Setup Modal ──── */}
      <AnimatePresence>
        {showEncryptionModal && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-[200] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
            onClick={() => setShowEncryptionModal(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.95, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-md bg-[#13161F] border border-[#2A2E3B] rounded-2xl p-6 shadow-2xl"
            >
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-[#2563EB]/10 flex items-center justify-center">
                    <Lock className="w-5 h-5 text-[#2563EB]" />
                  </div>
                  <h3 className="text-lg font-display font-medium text-white">Set Encryption Password</h3>
                </div>
                <button onClick={() => setShowEncryptionModal(false)} className="p-1 hover:bg-[#1A1D26] rounded-full text-[#8A93B2]">
                  <X className="w-4 h-4" />
                </button>
              </div>

              <p className="text-sm text-[#8A93B2] mb-5 leading-relaxed">
                Your data will be encrypted end-to-end before leaving this device. Choose a strong password — there is no recovery option.
              </p>

              <div className="space-y-4">
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'} value={encPassword}
                    onChange={(e) => setEncPassword(e.target.value)}
                    placeholder="Password (min 8 characters)"
                    className="w-full bg-[#0D0F16] border border-[#2A2E3B] rounded-lg px-4 py-3 text-sm text-[#F0F2F8] placeholder:text-[#8A93B2]/40 focus:border-[#2563EB] focus:outline-none"
                  />
                  <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-[#8A93B2] hover:text-white">
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                <input
                  type={showPassword ? 'text' : 'password'} value={encConfirm}
                  onChange={(e) => setEncConfirm(e.target.value)}
                  placeholder="Confirm password"
                  className="w-full bg-[#0D0F16] border border-[#2A2E3B] rounded-lg px-4 py-3 text-sm text-[#F0F2F8] placeholder:text-[#8A93B2]/40 focus:border-[#2563EB] focus:outline-none"
                />
              </div>

              <div className="flex gap-3 mt-6">
                <button onClick={() => setShowEncryptionModal(false)} className="flex-1 py-2.5 rounded-lg border border-[#2A2E3B] text-[#8A93B2] text-sm hover:bg-[#1A1D26] transition-colors">Cancel</button>
                <button onClick={handleEncryptionSetup} className="flex-1 py-2.5 rounded-lg bg-[#2563EB] text-white text-sm font-medium hover:bg-[#1E40AF] transition-colors">Enable Cloud Backup</button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};