'use client';

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import Link from 'next/link';
import {
  MessageSquareText,
  Sparkles,
  Send,
  Search,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  TrendingUp,
  TrendingDown,
  Minus,
  RefreshCw,
  Info,
  ShieldCheck,
  Building2,
  MapPin,
  Layers,
  ArrowRight,
  Filter,
  Globe2,
  FileText,
  Lightbulb,
  Radio,
  Lock,
  Mail,
  FileDown,
  Edit3,
  Save,
  CheckCircle,
  XCircle,
  History,
  Copy,
} from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

// Civic Topic Choices with Bilingual Descriptions
const CIVIC_TOPICS = [
  { id: 'roads', name: 'Roads & Potholes', kn: 'ರಸ್ತೆಗಳು ಮತ್ತು ಗುಂಡಿಗಳು', icon: '🛣️' },
  { id: 'waste_management', name: 'Garbage & Waste', kn: 'ತ್ಯಾಜ್ಯ ಮತ್ತು ನೈರ್ಮಲ್ಯ', icon: '🗑️' },
  { id: 'water_supply', name: 'Water Supply & Drainage', kn: 'ನೀರು ಮತ್ತು ಒಳಚರಂಡಿ', icon: '💧' },
  { id: 'traffic_and_transport', name: 'Traffic & Public Transit', kn: 'ಸಂಚಾರ ಮತ್ತು ಸಾರಿಗೆ', icon: '🚦' },
  { id: 'street_lighting', name: 'Street Lighting & Power', kn: 'ಬೀದಿ ದೀಪಗಳು ಮತ್ತು ವಿದ್ಯುತ್', icon: '💡' },
  { id: 'parks_and_environment', name: 'Parks & Environment', kn: 'ಉದ್ಯಾನವನಗಳು ಮತ್ತು ಪರಿಸರ', icon: '🌳' },
  { id: 'other', name: 'General Neighborhood Issue', kn: 'ಇತರ ನಾಗರಿಕ ಸಮಸ್ಯೆ', icon: '📍' },
];

const BANGALORE_LOCALITIES = [
  'All Areas',
  'Indiranagar',
  'Koramangala',
  'HSR Layout',
  'Whitefield',
  'Jayanagar',
  'JP Nagar',
  'BTM Layout',
  'Malleshwaram',
  'Kengeri',
  'Rajarajeshwari Nagar',
  'Yelahanka',
  'Electronic City',
  'Hebbal',
  'Vijayanagar',
];

interface ProviderConfigStatus {
  status: string;
  bluesky_configured: boolean;
  bluesky_base_url: string;
  youtube_configured: boolean;
  tavily_configured: boolean;
  total_source_records: number;
  total_analysis_records: number;
  total_citizen_submissions: number;
}

interface CivicVoiceTheme {
  theme_id: string;
  theme_label: string;
  description: string;
  record_count: number;
  evidence_record_ids: string[];
  source_links: string[];
  sentiment_breakdown: Record<string, number>;
}

interface CivicVoiceTrendItem {
  theme_id: string;
  theme_label: string;
  current_window_count: number;
  previous_window_count: number;
  change_count: number;
  status: string;
  evidence_record_ids: string[];
}

interface CivicVoiceSummaryFinding {
  finding_description: string;
  category: string;
  theme_label?: string | null;
  supporting_record_count: number;
  evidence_record_ids: string[];
  source_urls: string[];
  uncertainties?: string | null;
}

interface CivicVoiceExtractedSuggestion {
  suggestion: string;
  source_record_id: string;
  source_url: string;
  disclaimer: string;
}

interface CivicVoiceUniversalFinding {
  heading: string;
  explanation: string;
  category: string;
  supporting_evidence_count: number;
  evidence_record_ids: string[];
  source_urls: string[];
  earliest_date?: string | null;
  latest_date?: string | null;
  uncertainties?: string | null;
  evidence_strength?: string;
}

interface CivicVoiceProblemConcern {
  heading: string;
  description: string;
  problem_type: string;
  supporting_record_count: number;
  evidence_record_ids: string[];
  source_urls: string[];
  evidence_strength?: string;
}

interface CivicVoiceUniversalSuggestion {
  heading: string;
  suggestion: string;
  origin: 'source_author' | 'synthesized_civicvoice' | 'synthesized_model';
  source_record_id?: string | null;
  source_url?: string | null;
  disclaimer: string;
}

interface CivicVoiceViewpointContrast {
  topic_aspect: string;
  areas_of_agreement: string;
  points_of_disagreement: string;
  disputed_questions: string[];
}

interface CivicVoiceCleanSourceItem {
  publisher: string;
  title: string;
  published_at?: string | null;
  excerpt: string;
  url: string;
  source_type: string;
  language?: string | null;
}

interface CivicVoiceSummaryData {
  topic?: string | null;
  generated_at: string;

  // Universal Report Sections A - J
  topic_title?: string;
  introduction?: string;
  relevant_dates?: string | null;
  facts_vs_claims?: string | null;

  overall_summary?: string;

  positive_opinions?: CivicVoiceUniversalFinding[];
  positive_opinions_status?: string | null;

  negative_opinions?: CivicVoiceUniversalFinding[];
  negative_opinions_status?: string | null;

  problems_and_concerns?: CivicVoiceProblemConcern[];
  problems_and_concerns_status?: string | null;

  suggestions_and_improvements?: CivicVoiceUniversalSuggestion[];
  suggestions_status?: string | null;

  viewpoint_contrasts?: CivicVoiceViewpointContrast[];

  trends_overview?: string;
  trends_available?: boolean;
  trend_items?: CivicVoiceTrendItem[];

  clean_sources?: CivicVoiceCleanSourceItem[];

  sample_size_assessment?: string;
  coverage: {
    total_source_records: number;
    total_analyzed_records: number;
    provider_distribution: Record<string, number>;
    language_distribution: Record<string, number>;
    missing_timestamps_count: number;
    limitations: string[];
  };

  // Research and Validation metadata
  unresolved_questions?: string[];
  ai_synthesized?: boolean;
  ai_model?: string | null;
  validation_status?: string | null;
  validation_notes?: string[];

  // Backward compatibility
  findings?: CivicVoiceSummaryFinding[];
  extracted_suggestions?: CivicVoiceExtractedSuggestion[];
  conflicting_perspectives?: string[];
}

interface CivicVoiceTrendingItem {
  topic: string;
  record_count: number;
  citizen_opinions_count: number;
  total_activity_count: number;
  latest_activity: string | null;
  sample_title?: string | null;
}

interface ProviderCollectionStatus {
  provider: string;
  success: boolean;
  count: number;
  error_message?: string | null;
}

interface PublicSourceRecord {
  id: string;
  provider: string;
  topic?: string | null;
  title?: string | null;
  content?: string | null;
  url: string;
  author?: string | null;
  published_at?: string | null;
  collected_at: string;
  language?: string | null;
}

interface CitizenAggregatedData {
  total_submissions: number;
  topic_distribution: Record<string, number>;
  locality_distribution: Record<string, number>;
  language_distribution: Record<string, number>;
  privacy_notice: string;
}

interface CivicVoiceReportAuditItem {
  id: string;
  report_id: string;
  action: string;
  performed_by: string;
  previous_status?: string | null;
  new_status?: string | null;
  details_json?: any;
  created_at: string;
}

interface CivicVoiceReportItem {
  id: string;
  title: string;
  topic: string;
  geographic_scope: string;
  reporting_period_start?: string | null;
  reporting_period_end?: string | null;
  status: 'draft' | 'pending_review' | 'approved' | 'rejected' | 'sent' | 'send_failed';
  authority_name: string;
  department_name: string;
  recipient_email?: string | null;
  official_portal_url?: string | null;
  mapping_verified: boolean;
  mapping_source_url?: string | null;
  mapping_last_verified?: string | null;
  source_records_count: number;
  citizen_submissions_count: number;
  summary_content: string;
  recommendations: string;
  themes_summary?: any;
  sentiment_summary?: any;
  evidence_urls?: string[];
  limitations: string;
  content_hash: string;
  approved_by?: string | null;
  approved_at?: string | null;
  rejection_reason?: string | null;
  sent_at?: string | null;
  idempotency_key?: string | null;
  delivery_details?: any;
  created_at: string;
  updated_at: string;
  audits: CivicVoiceReportAuditItem[];
}

export default function CivicVoicePage() {
  const [activeTab, setActiveTab] = useState<'trending' | 'explore' | 'share' | 'summary' | 'reports'>('trending');
  const [exploreSubTab, setExploreSubTab] = useState<'public' | 'citizen'>('public');

  // Status & Metadata state
  const [statusData, setStatusData] = useState<ProviderConfigStatus | null>(null);
  const [loadingStatus, setLoadingStatus] = useState(false);

  // Search-First State
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTopic, setActiveTopic] = useState('Mysore Dasara 2026');
  const [loadingSearch, setLoadingSearch] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [searchPerformed, setSearchPerformed] = useState(false);
  const [providerStatuses, setProviderStatuses] = useState<ProviderCollectionStatus[]>([]);
  const [citizenOpinionsCount, setCitizenOpinionsCount] = useState<number>(0);

  // Trending Topics State
  const [trendingTopics, setTrendingTopics] = useState<CivicVoiceTrendingItem[]>([]);
  const [loadingTrending, setLoadingTrending] = useState(false);

  // Form State for Citizen Submission
  const [formTopic, setFormTopic] = useState('Mysore Dasara 2026');
  const [formLocality, setFormLocality] = useState('');
  const [formLanguage, setFormLanguage] = useState<'en' | 'kn'>('en');
  const [formOpinionText, setFormOpinionText] = useState('');
  const [formConsent, setFormConsent] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState<{
    id: string;
    topic: string;
    locality?: string | null;
    language?: string | null;
    created_at: string;
    confirmation_message: string;
  } | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Explore State
  const [selectedFilterTopic, setSelectedFilterTopic] = useState<string>('all');
  const [exploreFilterKeyword, setExploreFilterKeyword] = useState('');
  const [loadingExplore, setLoadingExplore] = useState(false);
  const [exploreError, setExploreError] = useState<string | null>(null);

  const [themes, setThemes] = useState<CivicVoiceTheme[]>([]);
  const [trends, setTrends] = useState<CivicVoiceTrendItem[]>([]);
  const [summaryData, setSummaryData] = useState<CivicVoiceSummaryData | null>(null);
  const [publicRecords, setPublicRecords] = useState<PublicSourceRecord[]>([]);
  const [citizenAggregated, setCitizenAggregated] = useState<CitizenAggregatedData | null>(null);
  const [expandedSourceIds, setExpandedSourceIds] = useState<Record<string, boolean>>({});
  const toggleSourceExpand = (id: string) => {
    setExpandedSourceIds((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  // Fetch status on mount
  const fetchStatus = useCallback(async () => {
    try {
      setLoadingStatus(true);
      const res = await fetch(`${API_BASE}/civicvoice/status`);
      if (res.ok) {
        const data = await res.json();
        setStatusData(data);
      }
    } catch {
      // Graceful fallback for local development
    } finally {
      setLoadingStatus(false);
    }
  }, []);

  // Fetch trending topics discovered from actual database records
  const fetchTrendingTopics = useCallback(async () => {
    try {
      setLoadingTrending(true);
      const res = await fetch(`${API_BASE}/civicvoice/trending?limit=12`);
      if (res.ok) {
        const data = await res.json();
        setTrendingTopics(data.trending_topics || []);
      }
    } catch {
      // Graceful fallback
    } finally {
      setLoadingTrending(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    fetchTrendingTopics();
  }, [fetchStatus, fetchTrendingTopics]);

  // Topic Search handler across external sources
  const handleSearch = async (targetQuery?: string, forceRefresh = false) => {
    const q = (targetQuery !== undefined ? targetQuery : searchQuery).trim();
    if (!q) return;

    setSearchQuery(q);
    setLoadingSearch(true);
    setSearchError(null);

    try {
      const res = await fetch(`${API_BASE}/civicvoice/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q, limit_per_provider: 5, force_refresh: forceRefresh }),
      });

      if (res.status === 429) {
        setSearchError('Search rate limit reached (max 20 per minute). Please wait a moment before trying again.');
        return;
      }

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Topic search request failed.');
      }

      const data = await res.json();
      setActiveTopic(data.topic);
      setPublicRecords(data.records || []);
      setSummaryData(data.summary || null);
      setThemes(data.themes || []);
      setTrends(data.trends?.trends || []);
      setProviderStatuses(data.provider_statuses || []);
      setCitizenOpinionsCount(data.citizen_submissions_count || 0);
      setFormTopic(data.topic);
      setSearchPerformed(true);

      // Navigate to summary brief view
      setActiveTab('summary');

      // Refresh trending topics from database
      fetchTrendingTopics();
    } catch (err: any) {
      setSearchError(err.message || 'An error occurred while searching civic topics.');
    } finally {
      setLoadingSearch(false);
    }
  };

  // Fetch explore intelligence data
  const fetchExploreData = useCallback(async () => {
    try {
      setLoadingExplore(true);
      setExploreError(null);

      const topicParam = selectedFilterTopic !== 'all' ? `?topic=${encodeURIComponent(selectedFilterTopic)}` : (activeTopic ? `?topic=${encodeURIComponent(activeTopic)}` : '');

      // Concurrent fetch across public read endpoints
      const [themesRes, trendsRes, summaryRes, recordsRes, citizenRes] = await Promise.allSettled([
        fetch(`${API_BASE}/civicvoice/themes${topicParam}`),
        fetch(`${API_BASE}/civicvoice/trends${topicParam ? `${topicParam}&window_days=7` : '?window_days=7'}`),
        fetch(`${API_BASE}/civicvoice/summary${topicParam}`),
        fetch(`${API_BASE}/civicvoice/records?limit=25${selectedFilterTopic !== 'all' ? `&topic=${encodeURIComponent(selectedFilterTopic)}` : (activeTopic ? `&topic=${encodeURIComponent(activeTopic)}` : '')}`),
        fetch(`${API_BASE}/civicvoice/submissions/aggregated${topicParam}`),
      ]);

      if (themesRes.status === 'fulfilled' && themesRes.value.ok) {
        const d = await themesRes.value.json();
        setThemes(d.themes || []);
      }
      if (trendsRes.status === 'fulfilled' && trendsRes.value.ok) {
        const d = await trendsRes.value.json();
        setTrends(d.trends || []);
      }
      if (summaryRes.status === 'fulfilled' && summaryRes.value.ok) {
        const d = await summaryRes.value.json();
        setSummaryData(d);
      }
      if (recordsRes.status === 'fulfilled' && recordsRes.value.ok) {
        const d = await recordsRes.value.json();
        setPublicRecords(d.records || []);
      }
      if (citizenRes.status === 'fulfilled' && citizenRes.value.ok) {
        const d = await citizenRes.value.json();
        setCitizenAggregated(d);
      }
    } catch (err: any) {
      setExploreError(err.message || 'Failed to load intelligence data');
    } finally {
      setLoadingExplore(false);
    }
  }, [selectedFilterTopic, activeTopic]);

  useEffect(() => {
    if (activeTab === 'explore') {
      fetchExploreData();
    }
  }, [activeTab, fetchExploreData]);

  // Handle citizen opinion submit
  const handleCitizenSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError(null);

    if (formOpinionText.trim().length < 10) {
      setSubmitError('Please enter at least 10 characters describing your opinion or suggestion.');
      return;
    }
    if (!formConsent) {
      setSubmitError('Please acknowledge consent to submit community civic opinion.');
      return;
    }

    try {
      setSubmitting(true);
      const res = await fetch(`${API_BASE}/civicvoice/submissions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          topic: formTopic.trim() || 'General Civic',
          opinion_text: formOpinionText.trim(),
          locality: formLocality.trim() || undefined,
          language: formLanguage,
          consent_given: formConsent,
        }),
      });

      if (res.status === 429) {
        throw new Error('Submission rate limit exceeded. Please wait a moment before submitting another opinion.');
      }

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || 'Failed to submit opinion. Please try again.');
      }

      const resData = await res.json();
      setSubmitSuccess(resData);
      setFormOpinionText('');
      setFormLocality('');
      setCitizenOpinionsCount((prev) => prev + 1);
      fetchStatus();
      fetchTrendingTopics();
    } catch (err: any) {
      setSubmitError(err.message || 'An unexpected error occurred during submission.');
    } finally {
      setSubmitting(false);
    }
  };

  // Filter public records by client search keyword
  const filteredPublicRecords = useMemo(() => {
    if (!exploreFilterKeyword.trim()) return publicRecords;
    const q = exploreFilterKeyword.toLowerCase();
    return publicRecords.filter(
      (r) =>
        (r.title && r.title.toLowerCase().includes(q)) ||
        (r.content && r.content.toLowerCase().includes(q)) ||
        (r.topic && r.topic.toLowerCase().includes(q))
    );
  }, [publicRecords, exploreFilterKeyword]);

  // =========================================================================
  // Reports State & Workflow Handlers (Prompt 4)
  // =========================================================================
  const [reportsAuthToken, setReportsAuthToken] = useState<string>('cv-verified-test-secret-2026');
  const [reportsList, setReportsList] = useState<CivicVoiceReportItem[]>([]);
  const [loadingReports, setLoadingReports] = useState(false);
  const [reportsFilterStatus, setReportsFilterStatus] = useState<string>('all');
  const [selectedReport, setSelectedReport] = useState<CivicVoiceReportItem | null>(null);

  // Generate Report Form
  const [generateTopic, setGenerateTopic] = useState('roads_infrastructure');
  const [generatePeriodDays, setGeneratePeriodDays] = useState(14);
  const [generateCustomTitle, setGenerateCustomTitle] = useState('');
  const [generatingReport, setGeneratingReport] = useState(false);

  // Edit Report Form
  const [isEditingReport, setIsEditingReport] = useState(false);
  const [editTitle, setEditTitle] = useState('');
  const [editSummary, setEditSummary] = useState('');
  const [editRecommendations, setEditRecommendations] = useState('');
  const [editLimitations, setEditLimitations] = useState('');
  const [editRecipientEmail, setEditRecipientEmail] = useState('');
  const [savingEdit, setSavingEdit] = useState(false);

  // Workflow Actions
  const [actionNotice, setActionNotice] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);
  const [approving, setApproving] = useState(false);
  const [rejecting, setRejecting] = useState(false);
  const [rejectReason, setRejectReason] = useState('');
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [sending, setSending] = useState(false);
  const [showSendModal, setShowSendModal] = useState(false);
  const [sendResult, setSendResult] = useState<any | null>(null);
  const [exportModalContent, setExportModalContent] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [copiedExport, setCopiedExport] = useState(false);

  const getAuthHeaders = useCallback(() => {
    const token = reportsAuthToken.trim() || 'cv-verified-test-secret-2026';
    return {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    };
  }, [reportsAuthToken]);

  const selectReport = useCallback((report: CivicVoiceReportItem) => {
    setSelectedReport(report);
    setEditTitle(report.title);
    setEditSummary(report.summary_content);
    setEditRecommendations(report.recommendations);
    setEditLimitations(report.limitations);
    setEditRecipientEmail(report.recipient_email || '');
    setIsEditingReport(false);
    setActionNotice(null);
    setSendResult(null);
  }, []);

  const fetchReports = useCallback(async () => {
    try {
      setLoadingReports(true);
      setActionNotice(null);
      const statusParam = reportsFilterStatus !== 'all' ? `?status=${encodeURIComponent(reportsFilterStatus)}` : '';
      const res = await fetch(`${API_BASE}/civicvoice/reports${statusParam}`, {
        headers: getAuthHeaders(),
      });
      if (res.ok) {
        const data = await res.json();
        const list: CivicVoiceReportItem[] = data.reports || [];
        setReportsList(list);
        if (selectedReport) {
          const fresh = list.find((r) => r.id === selectedReport.id);
          if (fresh) setSelectedReport(fresh);
        } else if (list.length > 0) {
          selectReport(list[0]);
        }
      } else if (res.status === 401 || res.status === 403) {
        setActionNotice({ type: 'error', text: 'Reviewer Authorization Required: Please supply a valid reviewer token.' });
      }
    } catch {
      // Graceful fallback
    } finally {
      setLoadingReports(false);
    }
  }, [reportsFilterStatus, getAuthHeaders, selectedReport, selectReport]);

  useEffect(() => {
    if (activeTab === 'reports') {
      fetchReports();
    }
  }, [activeTab, fetchReports]);

  const handleGenerateReport = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setGeneratingReport(true);
      setActionNotice(null);
      const res = await fetch(`${API_BASE}/civicvoice/reports/generate`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          topic: generateTopic,
          title: generateCustomTitle.trim() || undefined,
          reporting_period_days: generatePeriodDays,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to generate civic report.');
      }

      const newReport: CivicVoiceReportItem = await res.json();
      setActionNotice({ type: 'success', text: `Civic report '${newReport.title}' generated successfully in Draft status.` });
      setGenerateCustomTitle('');
      await fetchReports();
      selectReport(newReport);
    } catch (err: any) {
      setActionNotice({ type: 'error', text: err.message || 'Error generating report.' });
    } finally {
      setGeneratingReport(false);
    }
  };

  const handleSaveEdit = async () => {
    if (!selectedReport) return;
    try {
      setSavingEdit(true);
      setActionNotice(null);
      const res = await fetch(`${API_BASE}/civicvoice/reports/${selectedReport.id}`, {
        method: 'PATCH',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          title: editTitle,
          summary_content: editSummary,
          recommendations: editRecommendations,
          limitations: editLimitations,
          recipient_email: editRecipientEmail.trim() || undefined,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to save edits.');
      }

      const updated: CivicVoiceReportItem = await res.json();
      selectReport(updated);
      setIsEditingReport(false);
      setActionNotice({
        type: 'info',
        text: 'Report updated. Note: Prior approval was invalidated to guarantee review integrity; re-approval is required.',
      });
      fetchReports();
    } catch (err: any) {
      setActionNotice({ type: 'error', text: err.message || 'Error saving report edits.' });
    } finally {
      setSavingEdit(false);
    }
  };

  const handleApproveReport = async () => {
    if (!selectedReport) return;
    try {
      setApproving(true);
      setActionNotice(null);
      const res = await fetch(`${API_BASE}/civicvoice/reports/${selectedReport.id}/approve`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ notes: 'Approved after verification of evidence and recipient.' }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Approval failed.');
      }

      const updated: CivicVoiceReportItem = await res.json();
      selectReport(updated);
      setActionNotice({ type: 'success', text: 'Report successfully APPROVED and cryptographically bound with SHA-256 hash.' });
      fetchReports();
    } catch (err: any) {
      setActionNotice({ type: 'error', text: err.message || 'Approval error.' });
    } finally {
      setApproving(false);
    }
  };

  const handleRejectReport = async () => {
    if (!selectedReport || !rejectReason.trim()) return;
    try {
      setRejecting(true);
      setActionNotice(null);
      const res = await fetch(`${API_BASE}/civicvoice/reports/${selectedReport.id}/reject`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ reason: rejectReason.trim() }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Rejection failed.');
      }

      const updated: CivicVoiceReportItem = await res.json();
      selectReport(updated);
      setShowRejectModal(false);
      setRejectReason('');
      setActionNotice({ type: 'info', text: 'Report rejected. Review reason recorded in audit trail.' });
      fetchReports();
    } catch (err: any) {
      setActionNotice({ type: 'error', text: err.message || 'Rejection error.' });
    } finally {
      setRejecting(false);
    }
  };

  const handleSendReport = async () => {
    if (!selectedReport) return;
    try {
      setSending(true);
      setActionNotice(null);
      setSendResult(null);
      const res = await fetch(`${API_BASE}/civicvoice/reports/${selectedReport.id}/send`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ confirm_send: true }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Dispatch failed.');
      }

      const result = await res.json();
      setSendResult(result);
      setShowSendModal(false);
      setActionNotice({
        type: result.delivery_mode === 'resend_api' ? 'success' : 'info',
        text: result.message,
      });
      fetchReports();
    } catch (err: any) {
      setActionNotice({ type: 'error', text: err.message || 'Dispatch error.' });
    } finally {
      setSending(false);
    }
  };

  const handleExportReport = async () => {
    if (!selectedReport) return;
    try {
      setExporting(true);
      const res = await fetch(`${API_BASE}/civicvoice/reports/${selectedReport.id}/export`, {
        headers: getAuthHeaders(),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Export failed.');
      }
      const data = await res.json();
      setExportModalContent(data.content);
    } catch (err: any) {
      setActionNotice({ type: 'error', text: err.message || 'Export error.' });
    } finally {
      setExporting(false);
    }
  };


  return (
    <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8 space-y-8 flex-1">
      {/* Hero Header Section */}
      <section className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-10 shadow-xs relative overflow-hidden space-y-6">
        {/* Subtle Karnataka Flag Accent Edge */}
        <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-[#C8102E] via-[#FFC72C] to-[#C8102E]" />

        {/* Platform Branding Badge */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="inline-flex items-center gap-2 bg-red-50 border border-red-200/80 px-3.5 py-1.5 rounded-full text-xs font-bold text-[#C8102E] uppercase tracking-wider">
            <MessageSquareText className="w-3.5 h-3.5 text-amber-600" />
            <span>NammaNexus AI • Platform Hub · Bengaluru Civic Intelligence Platform</span>
          </div>

          {/* Live Provider Badges */}
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-600 bg-slate-50 px-3 py-1.5 rounded-full border border-slate-200">
            <span className="flex items-center gap-1.5">
              <Radio className="w-3 h-3 text-emerald-600 animate-pulse" />
              Live Sources:
            </span>
            <span className="flex items-center gap-1 text-[11px] font-bold text-slate-700">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> Bluesky
            </span>
            <span className="text-slate-300">•</span>
            <span className="flex items-center gap-1 text-[11px] font-bold text-slate-700">
              <span className={`w-1.5 h-1.5 rounded-full ${statusData?.youtube_configured ? 'bg-emerald-500' : 'bg-slate-300'}`} /> YouTube
            </span>
            <span className="text-slate-300">•</span>
            <span className="flex items-center gap-1 text-[11px] font-bold text-slate-700">
              <span className={`w-1.5 h-1.5 rounded-full ${statusData?.tavily_configured ? 'bg-emerald-500' : 'bg-slate-300'}`} /> Tavily
            </span>
          </div>
        </div>

        {/* Title & Subtitle */}
        <div className="max-w-3xl space-y-2">
          <h1 className="text-3xl sm:text-5xl font-black text-slate-900 tracking-tight leading-tight">
            CivicVoice — <span className="text-[#C8102E]">Public Opinion Intelligence</span>
          </h1>
          <p className="text-base sm:text-lg text-slate-600 font-medium">
            Discover topics. Understand perspectives. Share your opinion.
          </p>
        </div>

        {/* Main Search Field & Helper Text */}
        <div className="max-w-3xl space-y-2">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSearch();
            }}
            className="flex flex-col sm:flex-row items-stretch gap-2"
          >
            <div className="relative flex-1">
              <Search className="w-5 h-5 text-slate-400 absolute left-4 top-3.5" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search any topic, event, or public discussion…"
                className="w-full pl-12 pr-4 py-3.5 text-sm sm:text-base rounded-2xl border-2 border-slate-200 bg-white text-slate-900 placeholder-slate-400 focus:outline-hidden focus:border-[#C8102E] shadow-2xs transition-all"
              />
            </div>
            <button
              type="submit"
              disabled={loadingSearch}
              className="inline-flex items-center justify-center gap-2 bg-[#C8102E] hover:bg-[#A60C24] disabled:bg-slate-300 text-white font-bold px-6 py-3.5 rounded-2xl shadow-md transition-all text-sm group"
            >
              {loadingSearch ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin text-amber-300" />
                  <span>Searching...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4 text-amber-300 group-hover:scale-110 transition-transform" />
                  <span>Search</span>
                </>
              )}
            </button>
          </form>

          {/* Example Helper Text */}
          <div className="flex items-center gap-2 text-xs text-slate-500 pl-1">
            <span>Example:</span>
            <button
              type="button"
              onClick={() => {
                setSearchQuery('Mysore Dasara 2026');
                handleSearch('Mysore Dasara 2026');
              }}
              className="font-semibold text-[#C8102E] hover:underline bg-red-50 hover:bg-red-100 border border-red-200/80 px-2.5 py-0.5 rounded-md transition-colors cursor-pointer"
            >
              Mysore Dasara 2026
            </button>
            <span className="text-slate-300">•</span>
            <button
              type="button"
              onClick={() => {
                setSearchQuery('Bengaluru Metro Phase 2');
                handleSearch('Bengaluru Metro Phase 2');
              }}
              className="hover:underline text-slate-600 hover:text-slate-900 transition-colors cursor-pointer"
            >
              Bengaluru Metro Phase 2
            </button>
          </div>
        </div>

        {/* Search Error Notice */}
        {searchError && (
          <div className="p-4 rounded-2xl bg-red-50 border border-red-200 text-xs text-red-700 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
            <span>{searchError}</span>
          </div>
        )}

        {/* Partial Source Failure Notice */}
        {providerStatuses.some((p) => !p.success) && (
          <div className="p-4 rounded-2xl bg-amber-50 border border-amber-200 text-xs text-amber-900 flex items-start gap-2.5">
            <Info className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
            <div>
              <strong>Notice regarding data sources:</strong>
              {providerStatuses
                .filter((p) => !p.success)
                .map((p) => (
                  <div key={p.provider} className="mt-0.5">
                    • <span className="font-semibold capitalize">{p.provider}</span>: {p.error_message || 'Temporarily unavailable'}.
                  </div>
                ))}
              <span className="text-amber-700 text-[11px] block mt-1">
                Available intelligence compiled from active providers.
              </span>
            </div>
          </div>
        )}

        {/* Empty Results Banner */}
        {searchPerformed && publicRecords.length === 0 && !loadingSearch && (
          <div className="p-6 rounded-2xl bg-slate-50 border border-slate-200 text-center space-y-3">
            <div className="w-10 h-10 rounded-full bg-amber-100 text-amber-700 flex items-center justify-center mx-auto">
              <Search className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-slate-900 text-sm">No external discussions found for &quot;{activeTopic}&quot;</h3>
              <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
                No records discovered across Bluesky, YouTube, or Tavily. You can be the first to start the civic discussion by sharing your opinion!
              </p>
            </div>
            <button
              onClick={() => {
                setFormTopic(activeTopic);
                setActiveTab('share');
              }}
              className="inline-flex items-center gap-1.5 bg-[#C8102E] text-white text-xs font-bold px-4 py-2 rounded-xl shadow-xs hover:bg-[#A60C24] transition-colors"
            >
              <Send className="w-3.5 h-3.5 text-amber-300" />
              <span>Share Your Opinion on &quot;{activeTopic}&quot;</span>
            </button>
          </div>
        )}

        {/* Four Clear Navigation Options */}
        <div className="pt-4 border-t border-slate-100 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
          <div className="inline-flex p-1 bg-slate-100/90 rounded-2xl border border-slate-200/80 overflow-x-auto">
            <button
              onClick={() => setActiveTab('trending')}
              className={`flex items-center gap-2 px-4 sm:px-5 py-2.5 rounded-xl text-xs sm:text-sm font-bold transition-all whitespace-nowrap ${
                activeTab === 'trending'
                  ? 'bg-white text-[#C8102E] shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <TrendingUp className="w-4 h-4 text-amber-600" />
              <span>Trending topics</span>
              {trendingTopics.length > 0 && (
                <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-amber-100 text-amber-900 font-bold">
                  {trendingTopics.length}
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab('explore')}
              className={`flex items-center gap-2 px-4 sm:px-5 py-2.5 rounded-xl text-xs sm:text-sm font-bold transition-all whitespace-nowrap ${
                activeTab === 'explore'
                  ? 'bg-white text-[#C8102E] shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Sparkles className="w-4 h-4 text-amber-600" />
              <span>Explore opinions</span>
            </button>

            <button
              onClick={() => setActiveTab('share')}
              className={`flex items-center gap-2 px-4 sm:px-5 py-2.5 rounded-xl text-xs sm:text-sm font-bold transition-all whitespace-nowrap ${
                activeTab === 'share'
                  ? 'bg-white text-[#C8102E] shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Send className="w-4 h-4 text-[#C8102E]" />
              <span>Share your opinion</span>
              <span className="text-[10px] px-1.5 py-0.2 rounded bg-amber-100 text-amber-800 font-semibold hidden md:inline">
                ನಿಮ್ಮ ಧ್ವನಿ
              </span>
            </button>

            <button
              onClick={() => setActiveTab('summary')}
              className={`flex items-center gap-2 px-4 sm:px-5 py-2.5 rounded-xl text-xs sm:text-sm font-bold transition-all whitespace-nowrap ${
                activeTab === 'summary'
                  ? 'bg-white text-[#C8102E] shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <FileText className="w-4 h-4 text-[#C8102E]" />
              <span>Topic summaries</span>
            </button>

            <button
              onClick={() => setActiveTab('reports')}
              className={`flex items-center gap-2 px-3 py-2.5 rounded-xl text-xs sm:text-sm font-semibold transition-all whitespace-nowrap ${
                activeTab === 'reports'
                  ? 'bg-white text-emerald-700 shadow-xs font-bold'
                  : 'text-slate-500 hover:text-slate-800'
              }`}
              title="Verified Official Reporting for BBMP/BWSSB Authorities"
            >
              <Building2 className="w-3.5 h-3.5 text-emerald-600" />
              <span className="hidden lg:inline">Official Reports</span>
            </button>
          </div>

          <div className="text-xs text-slate-500 flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            <span>Citizen privacy strictly preserved • Deterministic grounding</span>
          </div>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* TAB 1: TRENDING TOPICS (Search-First)                                      */}
      {/* ========================================================================= */}
      {activeTab === 'trending' && (
        <section className="space-y-6 animate-in fade-in">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-xl font-extrabold text-slate-900 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-[#C8102E]" />
                Trending Topics
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Discovered from actual collected discussions and citizen feedback across Bengaluru and Karnataka. No fabricated counts.
              </p>
            </div>
            <button
              onClick={fetchTrendingTopics}
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-white border border-slate-200 px-3 py-1.5 rounded-xl shadow-2xs hover:bg-slate-50 transition-colors"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loadingTrending ? 'animate-spin' : ''}`} />
              <span>Refresh Trends</span>
            </button>
          </div>

          {loadingTrending && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="p-6 bg-white border border-slate-200 rounded-2xl animate-pulse space-y-3">
                  <div className="h-4 bg-slate-200 rounded w-2/3" />
                  <div className="h-3 bg-slate-100 rounded w-1/2" />
                  <div className="h-8 bg-slate-100 rounded w-full mt-4" />
                </div>
              ))}
            </div>
          )}

          {!loadingTrending && trendingTopics.length === 0 && (
            <div className="p-10 rounded-3xl bg-white border border-slate-200 text-center space-y-4 shadow-xs">
              <div className="w-12 h-12 rounded-2xl bg-amber-50 text-amber-700 flex items-center justify-center mx-auto">
                <TrendingUp className="w-6 h-6 text-amber-600" />
              </div>
              <div className="space-y-1">
                <h3 className="font-bold text-slate-900 text-base">No trending topics discovered yet</h3>
                <p className="text-xs text-slate-500 max-w-md mx-auto leading-relaxed">
                  Topics appear here automatically as public discussions are searched and collected. Try searching for &quot;Mysore Dasara 2026&quot; above to discover live perspectives!
                </p>
              </div>
              <button
                onClick={() => {
                  setSearchQuery('Mysore Dasara 2026');
                  handleSearch('Mysore Dasara 2026');
                }}
                className="inline-flex items-center gap-2 bg-[#C8102E] hover:bg-[#A60C24] text-white font-bold px-4 py-2.5 rounded-xl text-xs shadow-xs transition-colors"
              >
                <Search className="w-3.5 h-3.5 text-amber-300" />
                <span>Search &quot;Mysore Dasara 2026&quot;</span>
              </button>
            </div>
          )}

          {!loadingTrending && trendingTopics.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {trendingTopics.map((item) => (
                <div
                  key={item.topic}
                  className="bg-white border border-slate-200 hover:border-[#C8102E] rounded-2xl p-5 shadow-xs hover:shadow-sm transition-all flex flex-col justify-between space-y-4 group"
                >
                  <div className="space-y-2">
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="font-bold text-slate-900 text-base group-hover:text-[#C8102E] transition-colors leading-snug">
                        {item.topic}
                      </h3>
                      <span className="text-[10px] font-extrabold text-[#C8102E] bg-red-50 border border-red-200 px-2 py-0.5 rounded-full shrink-0">
                        {item.total_activity_count} {item.total_activity_count === 1 ? 'item' : 'items'}
                      </span>
                    </div>

                    {item.sample_title && (
                      <p className="text-xs text-slate-600 line-clamp-2 leading-relaxed">
                        &ldquo;{item.sample_title}&rdquo;
                      </p>
                    )}

                    <div className="pt-2 flex flex-wrap items-center gap-3 text-[11px] text-slate-500">
                      <span className="flex items-center gap-1">
                        <Globe2 className="w-3 h-3 text-slate-400" />
                        {item.record_count} external
                      </span>
                      <span>•</span>
                      <span className="flex items-center gap-1">
                        <MessageSquareText className="w-3 h-3 text-slate-400" />
                        {item.citizen_opinions_count} citizen
                      </span>
                      {item.latest_activity && (
                        <>
                          <span>•</span>
                          <span className="text-slate-400">
                            {new Date(item.latest_activity).toLocaleDateString()}
                          </span>
                        </>
                      )}
                    </div>
                  </div>

                  <div className="pt-3 border-t border-slate-100 flex items-center justify-between gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        setSearchQuery(item.topic);
                        handleSearch(item.topic);
                      }}
                      className="inline-flex items-center gap-1.5 text-xs font-bold text-[#C8102E] hover:text-[#A60C24] transition-colors cursor-pointer"
                    >
                      <span>View Summary</span>
                      <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
                    </button>

                    <button
                      type="button"
                      onClick={() => {
                        setFormTopic(item.topic);
                        setActiveTab('share');
                      }}
                      className="text-[11px] font-semibold text-slate-600 hover:text-slate-900 bg-slate-50 hover:bg-slate-100 border border-slate-200 px-2.5 py-1 rounded-lg transition-colors cursor-pointer"
                    >
                      Share Opinion
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      )}


      {/* ========================================================================= */}
      {/* TAB 1: SHARE YOUR OPINION                                                 */}
      {/* ========================================================================= */}
      {activeTab === 'share' && (
        <section className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Main Citizen Form */}
          <div className="lg:col-span-7 bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 shadow-xs space-y-6">
            <div className="border-b border-slate-100 pb-4">
              <h2 className="text-xl font-extrabold text-slate-900 flex items-center gap-2">
                <span>Submit Citizen Opinion</span>
                <span className="text-xs text-amber-800 bg-amber-100 border border-amber-200 px-2.5 py-0.5 rounded-full font-semibold">
                  English / ಕನ್ನಡ
                </span>
              </h2>
              <p className="text-xs text-slate-500 mt-1">
                Share your observation, complaint, or practical suggestion about civic infrastructure in your area.
              </p>
            </div>

            {submitSuccess ? (
              <div className="p-6 rounded-2xl bg-emerald-50 border border-emerald-200 space-y-4 animate-in fade-in">
                <div className="flex items-start gap-3">
                  <div className="w-9 h-9 rounded-xl bg-emerald-600 text-white flex items-center justify-center shrink-0">
                    <CheckCircle2 className="w-5 h-5" />
                  </div>
                  <div className="space-y-1">
                    <h3 className="font-extrabold text-slate-900 text-sm">
                      Opinion Recorded Successfully
                    </h3>
                    <p className="text-xs text-slate-700 leading-relaxed">
                      {submitSuccess.confirmation_message}
                    </p>
                  </div>
                </div>

                <div className="bg-white/80 p-3.5 rounded-xl border border-emerald-200 text-xs text-slate-600 space-y-1">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Submission ID:</span>
                    <span className="font-mono text-[11px] text-slate-800">{submitSuccess.id}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Topic Category:</span>
                    <span className="font-semibold text-slate-800 capitalize">{submitSuccess.topic.replace('_', ' ')}</span>
                  </div>
                  {submitSuccess.locality && (
                    <div className="flex justify-between">
                      <span className="text-slate-500">Locality:</span>
                      <span className="font-semibold text-slate-800">{submitSuccess.locality}</span>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <span className="text-slate-500">Language:</span>
                    <span className="font-semibold text-slate-800">{submitSuccess.language === 'kn' ? 'Kannada (ಕನ್ನಡ)' : 'English'}</span>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => setSubmitSuccess(null)}
                  className="w-full bg-[#C8102E] hover:bg-[#A60C24] text-white font-bold text-xs py-2.5 rounded-xl transition-colors shadow-2xs"
                >
                  Submit Another Opinion / ಇನ್ನೊಂದು ಅಭಿಪ್ರಾಯ ತಿಳಿಸಿ
                </button>
              </div>
            ) : (
              <form onSubmit={handleCitizenSubmit} className="space-y-5">
                {submitError && (
                  <div className="p-3.5 rounded-xl bg-red-50 border border-red-200 text-xs text-red-700 flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
                    <span>{submitError}</span>
                  </div>
                )}

                {/* Topic Input with Pre-fill & Quick Options */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <label className="block text-xs font-bold text-slate-800">
                      Topic / ವಿಷಯ <span className="text-red-500">*</span>
                    </label>
                    <span className="text-[11px] text-slate-400">Share about searched topic or enter a new topic</span>
                  </div>
                  <input
                    type="text"
                    value={formTopic}
                    onChange={(e) => setFormTopic(e.target.value)}
                    placeholder="e.g. Mysore Dasara 2026, Indiranagar Drainage, Metro Phase 2..."
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-xs bg-white text-slate-900 focus:outline-hidden focus:border-[#C8102E] font-medium"
                    required
                  />
                  <div className="flex flex-wrap items-center gap-1.5 pt-1">
                    <span className="text-[10px] text-slate-400">Suggestions:</span>
                    {CIVIC_TOPICS.slice(0, 5).map((top) => (
                      <button
                        key={top.id}
                        type="button"
                        onClick={() => setFormTopic(top.name)}
                        className={`text-[10px] px-2 py-0.5 rounded-md border transition-colors ${
                          formTopic === top.name
                            ? 'bg-red-50 text-[#C8102E] border-red-200 font-bold'
                            : 'bg-slate-50 hover:bg-slate-100 text-slate-600 border-slate-200'
                        }`}
                      >
                        {top.icon} {top.name}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Locality & Language Row */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="block text-xs font-bold text-slate-800">
                      Neighborhood / Locality (ಬಡಾವಣೆ)
                    </label>
                    <select
                      value={formLocality}
                      onChange={(e) => setFormLocality(e.target.value)}
                      className="w-full px-3 py-2 text-xs rounded-xl border border-slate-200 bg-white text-slate-800 focus:outline-hidden focus:border-[#C8102E] transition-colors"
                    >
                      <option value="">Select or choose area (optional)</option>
                      {BANGALORE_LOCALITIES.filter((l) => l !== 'All Areas').map((loc) => (
                        <option key={loc} value={loc}>
                          {loc}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="space-y-1.5">
                    <label className="block text-xs font-bold text-slate-800">
                      Language / ಭಾಷೆ
                    </label>
                    <div className="flex rounded-xl border border-slate-200 p-0.5 bg-slate-50">
                      <button
                        type="button"
                        onClick={() => setFormLanguage('en')}
                        className={`flex-1 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                          formLanguage === 'en'
                            ? 'bg-white text-slate-900 shadow-2xs font-bold'
                            : 'text-slate-600 hover:text-slate-900'
                        }`}
                      >
                        English
                      </button>
                      <button
                        type="button"
                        onClick={() => setFormLanguage('kn')}
                        className={`flex-1 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                          formLanguage === 'kn'
                            ? 'bg-[#C8102E] text-white shadow-2xs font-bold'
                            : 'text-slate-600 hover:text-slate-900'
                        }`}
                      >
                        ಕನ್ನಡ (Kannada)
                      </button>
                    </div>
                  </div>
                </div>

                {/* Opinion Text */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <label className="block text-xs font-bold text-slate-800">
                      Your Opinion or Suggestion / ನಿಮ್ಮ ಅಭಿಪ್ರಾಯ ಅಥವಾ ಸಲಹೆ <span className="text-red-500">*</span>
                    </label>
                    <span className={`text-[11px] ${formOpinionText.length > 2000 ? 'text-red-600 font-bold' : 'text-slate-400'}`}>
                      {formOpinionText.length} / 2000
                    </span>
                  </div>
                  <textarea
                    rows={5}
                    value={formOpinionText}
                    onChange={(e) => setFormOpinionText(e.target.value)}
                    placeholder={
                      formLanguage === 'kn'
                        ? 'ಉದಾ: ನಮ್ಮ ಬಡಾವಣೆಯಲ್ಲಿ ರಸ್ತೆ ಗುಂಡಿಗಳಿಂದ ಸಂಚಾರಕ್ಕೆ ತೊಂದರೆಯಾಗಿದೆ. ಸರಿಪಡಿಸಲು ಕ್ರಮ ಕೈಗೊಳ್ಳಿ...'
                        : 'e.g. Broken pavement near the metro station forces pedestrians onto the heavy traffic road. Suggest installing pedestrian barriers...'
                    }
                    className="w-full px-3.5 py-3 text-xs rounded-xl border border-slate-200 text-slate-800 placeholder-slate-400 focus:outline-hidden focus:border-[#C8102E] transition-colors leading-relaxed"
                  />
                  <p className="text-[11px] text-slate-500">
                    Minimum 10 characters. Avoid sharing personally identifiable details (phone numbers or passwords).
                  </p>
                </div>

                {/* Consent Checkbox */}
                <div className="p-3.5 rounded-xl bg-amber-50/70 border border-amber-200/80 flex items-start gap-3">
                  <input
                    type="checkbox"
                    id="consentCheckbox"
                    checked={formConsent}
                    onChange={(e) => setFormConsent(e.target.checked)}
                    className="mt-0.5 h-4 w-4 rounded text-[#C8102E] focus:ring-red-400 border-slate-300"
                  />
                  <label htmlFor="consentCheckbox" className="text-xs text-slate-700 leading-relaxed cursor-pointer select-none">
                    <strong>Consent & Privacy:</strong> I consent to the anonymous aggregation of my civic feedback into
                    neighborhood priority intelligence. I understand that my individual submission is confidential, will not
                    be published as raw personal text on the public web, and does not constitute an official municipal grievance
                    ticket or guarantee immediate administrative dispatch.
                  </label>
                </div>

                {/* Submit Action */}
                <button
                  type="submit"
                  disabled={submitting || formOpinionText.trim().length < 10 || !formConsent}
                  className="w-full bg-[#C8102E] hover:bg-[#A60C24] disabled:bg-slate-200 disabled:text-slate-400 text-white font-bold text-xs py-3.5 rounded-xl transition-all shadow-xs flex items-center justify-center gap-2 group"
                >
                  {submitting ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin text-white" />
                      <span>Recording Your Opinion...</span>
                    </>
                  ) : (
                    <>
                      <Send className="w-4 h-4 text-amber-300 group-hover:translate-x-0.5 transition-transform" />
                      <span>Submit Citizen Opinion / ಅಭಿಪ್ರಾಯ ಸಲ್ಲಿಸಿ</span>
                    </>
                  )}
                </button>
              </form>
            )}
          </div>

          {/* Educational Sidebar: How CivicVoice Works */}
          <div className="lg:col-span-5 space-y-6">
            <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-xs space-y-4">
              <h3 className="font-extrabold text-slate-900 text-sm flex items-center gap-2">
                <Info className="w-4 h-4 text-[#C8102E]" />
                How Citizen Voices Shape Action
              </h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                NammaNexus AI does not simply count isolated complaints. CivicVoice clusters similar neighborhood issues
                together to find patterns in urban neglect:
              </p>

              <div className="space-y-3 pt-2 text-xs">
                <div className="flex gap-3">
                  <div className="w-7 h-7 rounded-lg bg-red-50 text-[#C8102E] flex items-center justify-center font-bold shrink-0">
                    1
                  </div>
                  <div>
                    <h4 className="font-bold text-slate-900">Categorization & Sentiment</h4>
                    <p className="text-slate-500 text-[11px] leading-relaxed">
                      Rule-based multilingual intelligence categorizes complaints, positive community feedback, and recommendations.
                    </p>
                  </div>
                </div>

                <div className="flex gap-3">
                  <div className="w-7 h-7 rounded-lg bg-amber-50 text-amber-800 flex items-center justify-center font-bold shrink-0">
                    2
                  </div>
                  <div>
                    <h4 className="font-bold text-slate-900">Theme Clustering</h4>
                    <p className="text-slate-500 text-[11px] leading-relaxed">
                      Groups related neighborhood issues (e.g. road quality, garbage dumping, sewage backflow) to measure grievance volume.
                    </p>
                  </div>
                </div>

                <div className="flex gap-3">
                  <div className="w-7 h-7 rounded-lg bg-emerald-50 text-emerald-800 flex items-center justify-center font-bold shrink-0">
                    3
                  </div>
                  <div>
                    <h4 className="font-bold text-slate-900">Prioritization for SpotFix</h4>
                    <p className="text-slate-500 text-[11px] leading-relaxed">
                      Frequent community grievances highlight urgent spots for field photo verification and official dispatch.
                    </p>
                  </div>
                </div>
              </div>

              <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
                <span className="text-slate-500">Need immediate field photo reporting?</span>
                <Link
                  href="/spotfix"
                  className="font-bold text-[#C8102E] hover:underline flex items-center gap-1"
                >
                  SpotFix AI Intake <ArrowRight className="w-3 h-3" />
                </Link>
              </div>
            </div>

            {/* Privacy Guarantee Box */}
            <div className="bg-gradient-to-br from-amber-50/50 to-red-50/30 border border-amber-200/80 rounded-3xl p-6 shadow-xs space-y-2.5">
              <div className="flex items-center gap-2 text-xs font-bold text-amber-900">
                <ShieldCheck className="w-4 h-4 text-emerald-600" />
                <span>Zero-Tracking Privacy Standard</span>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed">
                Your submissions are stored without telephone numbers, email addresses, social profile links, or advertising
                trackers. CivicVoice measures aggregate public priorities, not individual identities.
              </p>
            </div>
          </div>
        </section>
      )}

      {/* ========================================================================= */}
      {/* TAB 2: EXPLORE PUBLIC OPINIONS                                            */}
      {/* ========================================================================= */}
      {activeTab === 'explore' && (
        <section className="space-y-6 animate-in fade-in">
          {/* Active Topic Indicator Banner */}
          {activeTopic && (
            <div className="bg-red-50/70 border border-red-200/90 rounded-2xl p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-[10px] font-bold text-[#C8102E] bg-white border border-red-200 px-2.5 py-0.5 rounded uppercase">
                  Active Topic
                </span>
                <span className="font-black text-slate-900 text-sm">{activeTopic}</span>
                <span className="text-xs text-slate-500 font-medium">
                  ({publicRecords.length} external sources • {citizenOpinionsCount} citizen voices)
                </span>
              </div>
              <button
                type="button"
                onClick={() => {
                  setFormTopic(activeTopic);
                  setActiveTab('share');
                }}
                className="text-xs font-bold text-[#C8102E] hover:text-[#A60C24] flex items-center gap-1 cursor-pointer"
              >
                <span>Share opinion on this topic</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          {/* Controls Bar: Filter & Search */}
          <div className="bg-white border border-slate-200 rounded-3xl p-4 sm:p-6 shadow-xs flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-bold text-slate-700 flex items-center gap-1.5 mr-1">
                <Filter className="w-3.5 h-3.5 text-[#C8102E]" /> Filter Topic:
              </span>
              <button
                type="button"
                onClick={() => setSelectedFilterTopic('all')}
                className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                  selectedFilterTopic === 'all'
                    ? 'bg-[#C8102E] text-white shadow-2xs font-bold'
                    : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                }`}
              >
                All Topics
              </button>
              {CIVIC_TOPICS.map((t) => (
                <button
                  type="button"
                  key={t.id}
                  onClick={() => setSelectedFilterTopic(t.id)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                    selectedFilterTopic === t.id
                      ? 'bg-[#C8102E] text-white shadow-2xs font-bold'
                      : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                  }`}
                >
                  {t.name}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-2">
              <div className="relative flex-1 md:w-64">
                <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-3" />
                <input
                  type="text"
                  value={exploreFilterKeyword}
                  onChange={(e) => setExploreFilterKeyword(e.target.value)}
                  placeholder="Search keywords in records..."
                  className="w-full pl-9 pr-3 py-2 text-xs rounded-xl border border-slate-200 bg-white text-slate-800 placeholder-slate-400 focus:outline-hidden focus:border-[#C8102E]"
                />
              </div>
              <button
                type="button"
                onClick={fetchExploreData}
                title="Refresh explore data"
                className="p-2 rounded-xl border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-600 transition-colors"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loadingExplore ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>

          {exploreError && (
            <div className="p-4 rounded-2xl bg-red-50 border border-red-200 text-xs text-red-700 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
              <span>{exploreError}</span>
            </div>
          )}

          {/* Small Sample Warning Disclaimer */}
          {summaryData && summaryData.coverage && summaryData.coverage.total_analyzed_records < 10 && (
            <div className="p-4 rounded-2xl bg-amber-50 border border-amber-200/90 text-xs text-amber-900 flex items-start gap-3">
              <Info className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
              <div>
                <strong>Sample Observability Notice:</strong> The current data sample contains{' '}
                {summaryData.coverage.total_analyzed_records} analyzed record(s). Findings reflect observed public data
                points from verified providers and community inputs, not an exhaustive scientific consensus across all
                Bengaluru wards.
              </div>
            </div>
          )}

          {/* Grid: Themes & Trends */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
            {/* Recurring Themes Section */}
            <div className="lg:col-span-7 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-base font-extrabold text-slate-900 flex items-center gap-2">
                    <FileText className="w-4 h-4 text-[#C8102E]" />
                    Recurring Civic Themes
                  </h3>
                  <p className="text-xs text-slate-500">Clustered from verified public source records</p>
                </div>
                <span className="text-xs text-slate-500 font-semibold">
                  {themes.length} {themes.length === 1 ? 'theme' : 'themes'}
                </span>
              </div>

              {themes.length === 0 ? (
                <div className="p-8 rounded-3xl bg-white border border-slate-200 text-center space-y-2">
                  <p className="text-xs text-slate-500">No themes detected for this topic yet.</p>
                  <p className="text-[11px] text-slate-400">
                    As new records are collected and analyzed, recurring patterns will appear here.
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {themes.map((th) => (
                    <div
                      key={th.theme_id}
                      className="bg-white border border-slate-200 rounded-2xl p-5 shadow-xs space-y-3"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <span className="text-[10px] uppercase font-bold text-[#C8102E] bg-red-50 border border-red-200 px-2 py-0.5 rounded">
                            {th.theme_id.replace('_', ' ')}
                          </span>
                          <h4 className="font-extrabold text-slate-900 text-sm mt-1">{th.theme_label}</h4>
                          <p className="text-xs text-slate-600 mt-1">{th.description}</p>
                        </div>
                        <div className="text-right shrink-0">
                          <span className="text-sm font-black text-slate-900">{th.record_count}</span>
                          <span className="text-[10px] text-slate-400 block">records</span>
                        </div>
                      </div>

                      {/* Sentiment breakdown pill */}
                      {th.sentiment_breakdown && (
                        <div className="pt-2 border-t border-slate-100 flex flex-wrap items-center gap-2 text-[10px]">
                          <span className="text-slate-400 font-medium">Sentiment breakdown:</span>
                          {Object.entries(th.sentiment_breakdown).map(([sent, cnt]) => (
                            <span
                              key={sent}
                              className={`px-2 py-0.5 rounded-full font-semibold ${
                                sent === 'negative'
                                  ? 'bg-red-50 text-red-700 border border-red-200'
                                  : sent === 'positive'
                                  ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                  : 'bg-slate-100 text-slate-700'
                              }`}
                            >
                              {sent}: {cnt}
                            </span>
                          ))}
                        </div>
                      )}

                      {/* Source Link Evidence */}
                      {th.source_links && th.source_links.length > 0 && (
                        <div className="pt-1 flex flex-wrap items-center gap-2 text-[11px]">
                          <span className="text-slate-400">Sample Sources:</span>
                          {th.source_links.slice(0, 3).map((linkUrl, i) => (
                            <a
                              key={i}
                              href={linkUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-[#C8102E] hover:underline flex items-center gap-1 font-semibold"
                            >
                              Source {i + 1} <ExternalLink className="w-2.5 h-2.5" />
                            </a>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Emerging Trends & Suggestions Section */}
            <div className="lg:col-span-5 space-y-6">
              {/* Trends Card */}
              <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-xs space-y-4">
                <div>
                  <div className="flex items-center justify-between">
                    <h3 className="font-extrabold text-slate-900 text-sm flex items-center gap-2">
                      <TrendingUp className="w-4 h-4 text-amber-600" />
                      Emerging Trends (7-Day Windows)
                    </h3>
                  </div>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    Changes in observed record counts between consecutive 7-day intervals.
                  </p>
                </div>

                {trends.length === 0 ? (
                  <p className="text-xs text-slate-400 py-3 text-center">No trend comparisons available yet.</p>
                ) : (
                  <div className="space-y-2.5">
                    {trends.map((tr) => (
                      <div
                        key={tr.theme_id}
                        className="p-3 rounded-xl bg-slate-50 border border-slate-200/80 flex items-center justify-between text-xs"
                      >
                        <div>
                          <span className="font-bold text-slate-900 block">{tr.theme_label}</span>
                          <span className="text-[10px] text-slate-500">
                            Current: {tr.current_window_count} • Prev: {tr.previous_window_count}
                          </span>
                        </div>
                        <div className="flex items-center gap-1.5 font-bold">
                          {tr.status === 'increasing' ? (
                            <span className="text-red-700 bg-red-100/80 px-2 py-0.5 rounded-full flex items-center gap-1 text-[11px]">
                              <TrendingUp className="w-3 h-3" /> +{tr.change_count}
                            </span>
                          ) : tr.status === 'decreasing' ? (
                            <span className="text-emerald-700 bg-emerald-100/80 px-2 py-0.5 rounded-full flex items-center gap-1 text-[11px]">
                              <TrendingDown className="w-3 h-3" /> {tr.change_count}
                            </span>
                          ) : (
                            <span className="text-slate-600 bg-slate-200/80 px-2 py-0.5 rounded-full flex items-center gap-1 text-[11px]">
                              <Minus className="w-3 h-3" /> Stable
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                <div className="text-[10px] text-slate-400 leading-relaxed pt-2 border-t border-slate-100">
                  <em>Disclaimer:</em> Trends reflect observed frequency in collected public data, not verified causal proof of municipal changes.
                </div>
              </div>

              {/* Community Suggestions Card */}
              {summaryData && summaryData.extracted_suggestions && summaryData.extracted_suggestions.length > 0 && (
                <div className="bg-gradient-to-br from-amber-50/40 via-white to-red-50/20 border border-amber-200/80 rounded-3xl p-6 shadow-xs space-y-3">
                  <h3 className="font-extrabold text-slate-900 text-sm flex items-center gap-2">
                    <Lightbulb className="w-4 h-4 text-amber-600" />
                    Community Suggestions Highlight
                  </h3>
                  <div className="space-y-3">
                    {summaryData.extracted_suggestions.slice(0, 4).map((sugg, idx) => (
                      <div key={idx} className="bg-white p-3 rounded-xl border border-slate-200 text-xs space-y-1">
                        <p className="text-slate-800 leading-relaxed font-medium">"{sugg.suggestion}"</p>
                        <div className="flex items-center justify-between text-[10px] text-slate-400 pt-1">
                          <span>{sugg.disclaimer}</span>
                          {sugg.source_url && (
                            <a
                              href={sugg.source_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-[#C8102E] hover:underline flex items-center gap-0.5 font-semibold"
                            >
                              Post <ExternalLink className="w-2.5 h-2.5" />
                            </a>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* ===================================================================== */}
          {/* EVIDENCE EXPLORER: PUBLIC RECORDS VS CITIZEN SUBMISSIONS              */}
          {/* ===================================================================== */}
          <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 shadow-xs space-y-6">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
              <div>
                <h3 className="text-lg font-extrabold text-slate-900">
                  Explorable Opinions & Community Voice Records
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Inspect the actual evidence behind every analyzed score and summary finding.
                </p>
              </div>

              {/* Sub-tab switcher to cleanly distinguish external from citizen data */}
              <div className="inline-flex p-1 bg-slate-100 rounded-xl border border-slate-200 text-xs font-bold">
                <button
                  type="button"
                  onClick={() => setExploreSubTab('public')}
                  className={`px-3 py-1.5 rounded-lg transition-all ${
                    exploreSubTab === 'public'
                      ? 'bg-white text-slate-900 shadow-2xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  Public Source Posts ({filteredPublicRecords.length})
                </button>
                <button
                  type="button"
                  onClick={() => setExploreSubTab('citizen')}
                  className={`px-3 py-1.5 rounded-lg transition-all ${
                    exploreSubTab === 'citizen'
                      ? 'bg-[#C8102E] text-white shadow-2xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  Citizen Submissions Aggregated ({citizenAggregated?.total_submissions ?? 0})
                </button>
              </div>
            </div>

            {/* Sub-tab 1: Public Source Posts */}
            {exploreSubTab === 'public' && (
              <div className="space-y-3">
                <div className="text-[11px] text-slate-500 bg-slate-50 p-3 rounded-xl border border-slate-200 flex items-center gap-2">
                  <Globe2 className="w-4 h-4 text-slate-600 shrink-0" />
                  <span>
                    <strong>External Public Provenance:</strong> These records are collected from permitted public
                    platforms (Bluesky, YouTube, Tavily). Clicking the post URL opens the original live source.
                  </span>
                </div>

                {filteredPublicRecords.length === 0 ? (
                  <p className="text-xs text-slate-400 py-8 text-center">
                    No external public records found matching the current criteria.
                  </p>
                ) : (
                  <div className="divide-y divide-slate-100">
                    {filteredPublicRecords.map((rec) => (
                      <div key={rec.id} className="py-4 space-y-2 text-xs">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-slate-900 uppercase text-[10px] px-2 py-0.5 rounded bg-slate-100 border border-slate-200">
                              {rec.provider}
                            </span>
                            {rec.topic && (
                              <span className="text-[10px] text-amber-800 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded">
                                {rec.topic}
                              </span>
                            )}
                            {rec.language && (
                              <span className="text-[10px] text-slate-500">
                                lang: {rec.language}
                              </span>
                            )}
                          </div>
                          <span className="text-[10px] text-slate-400">
                            {rec.published_at ? new Date(rec.published_at).toLocaleDateString() : 'Date unavailable'}
                          </span>
                        </div>

                        {rec.title && (
                          <h5 className="font-bold text-slate-900 text-xs">{rec.title}</h5>
                        )}
                        <div className="text-slate-600 leading-relaxed text-xs">
                          {rec.content && rec.content.length > 220 && !expandedSourceIds[rec.id] ? (
                            <>
                              <span>{rec.content.slice(0, 220)}...</span>
                              <button
                                type="button"
                                onClick={() => toggleSourceExpand(rec.id)}
                                className="ml-1.5 text-[#C8102E] hover:underline font-semibold cursor-pointer text-[11px]"
                              >
                                Show full excerpt
                              </button>
                            </>
                          ) : (
                            <>
                              <span>{rec.content || 'No text snippet available.'}</span>
                              {rec.content && rec.content.length > 220 && (
                                <button
                                  type="button"
                                  onClick={() => toggleSourceExpand(rec.id)}
                                  className="ml-1.5 text-slate-400 hover:text-slate-600 hover:underline font-semibold cursor-pointer text-[11px]"
                                >
                                  (Collapse)
                                </button>
                              )}
                            </>
                          )}
                        </div>

                        <div className="flex items-center justify-between pt-1">
                          <span className="text-[10px] text-slate-400 font-mono">ID: {rec.id.slice(0, 8)}...</span>
                          {rec.url && (
                            <a
                              href={rec.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-[#C8102E] hover:underline flex items-center gap-1 font-semibold text-[11px]"
                            >
                              View Original Post <ExternalLink className="w-3 h-3" />
                            </a>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Sub-tab 2: Citizen Community Voices (Anonymized Aggregate View) */}
            {exploreSubTab === 'citizen' && (
              <div className="space-y-4">
                <div className="text-[11px] text-[#C8102E] bg-red-50/50 p-4 rounded-xl border border-red-200/80 space-y-1">
                  <div className="flex items-center gap-2 font-bold">
                    <ShieldCheck className="w-4 h-4 text-[#C8102E] shrink-0" />
                    <span>Citizen Privacy & Confidentiality Guarantee</span>
                  </div>
                  <p className="text-slate-600 leading-relaxed">
                    {citizenAggregated?.privacy_notice ||
                      'Citizen submissions are kept strictly confidential and aggregated into civic priority insights. Raw individual texts and personal identifiers are never exposed publicly.'}
                  </p>
                </div>

                {!citizenAggregated || citizenAggregated.total_submissions === 0 ? (
                  <p className="text-xs text-slate-400 py-8 text-center">
                    No citizen submissions recorded for this topic yet. Be the first to share your opinion!
                  </p>
                ) : (
                  <div className="space-y-4">
                    {/* Metrics Grid */}
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 text-center">
                        <span className="text-[10px] text-slate-500 font-medium block">Total Community Voices</span>
                        <span className="text-2xl font-black text-[#C8102E] mt-1 block">
                          {citizenAggregated.total_submissions}
                        </span>
                        <span className="text-[10px] text-slate-400 block mt-0.5">Direct Resident Feedback</span>
                      </div>

                      <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 text-center">
                        <span className="text-[10px] text-slate-500 font-medium block">Localities Represented</span>
                        <span className="text-2xl font-black text-slate-800 mt-1 block">
                          {Object.keys(citizenAggregated.locality_distribution).length}
                        </span>
                        <span className="text-[10px] text-slate-400 block mt-0.5">Bengaluru Neighborhoods</span>
                      </div>

                      <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 text-center">
                        <span className="text-[10px] text-slate-500 font-medium block">Languages Represented</span>
                        <div className="flex items-center justify-center gap-2 mt-1.5 text-xs font-bold text-slate-700">
                          <span>English: {citizenAggregated.language_distribution['en'] || 0}</span>
                          <span>•</span>
                          <span>ಕನ್ನಡ: {citizenAggregated.language_distribution['kn'] || 0}</span>
                        </div>
                        <span className="text-[10px] text-slate-400 block mt-0.5">Bilingual Community Voice</span>
                      </div>
                    </div>

                    {/* Topic Distribution Breakdown */}
                    <div className="bg-slate-50/60 p-4 rounded-xl border border-slate-200 space-y-2">
                      <h4 className="text-xs font-bold text-slate-900">Community Concern Breakdown by Topic:</h4>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                        {Object.entries(citizenAggregated.topic_distribution).map(([topKey, count]) => (
                          <div
                            key={topKey}
                            className="bg-white p-2.5 rounded-lg border border-slate-200 flex items-center justify-between"
                          >
                            <span className="font-semibold text-slate-800 capitalize">
                              {topKey.replace('_', ' ')}
                            </span>
                            <span className="text-xs font-bold text-[#C8102E] bg-red-50 border border-red-200 px-2 py-0.5 rounded">
                              {count} {count === 1 ? 'opinion' : 'opinions'}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Active Localities Representation */}
                    {Object.keys(citizenAggregated.locality_distribution).length > 0 && (
                      <div className="bg-slate-50/60 p-4 rounded-xl border border-slate-200 space-y-2">
                        <h4 className="text-xs font-bold text-slate-900">Active Neighborhoods:</h4>
                        <div className="flex flex-wrap gap-1.5 text-xs">
                          {Object.entries(citizenAggregated.locality_distribution).map(([locName, count]) => (
                            <span
                              key={locName}
                              className="bg-white px-2.5 py-1 rounded-lg border border-slate-200 text-slate-700 font-medium flex items-center gap-1.5 text-[11px]"
                            >
                              <MapPin className="w-3 h-3 text-[#C8102E]" />
                              {locName} ({count})
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </section>
      )}

      {/* ========================================================================= */}
      {/* TAB 4: TOPIC SUMMARIES (Search-First Intelligence Brief)                  */}
      {/* ========================================================================= */}
      {activeTab === 'summary' && (
        <section className="space-y-8 animate-in fade-in">
          {/* ========================================================================= */}
          {/* TOP SUMMARY OVERVIEW CARD (Required by Section 3)                          */}
          {/* ========================================================================= */}
          <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 shadow-xs space-y-6 relative overflow-hidden">
            <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-[#C8102E] via-[#FFC72C] to-[#C8102E]" />

            {/* Header Row: Topic Title, Badge, and Action Buttons */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-100 pb-5">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <div className="inline-flex items-center gap-1.5 bg-red-50 border border-red-200 text-[#C8102E] px-2.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider">
                    <Sparkles className="w-3 h-3 text-amber-500" />
                    <span>Public Opinion Intelligence Report</span>
                  </div>
                  {summaryData?.ai_synthesized ? (
                    <div className="inline-flex items-center gap-1.5 bg-indigo-50 border border-indigo-200 text-indigo-700 px-2.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider">
                      <Sparkles className="w-3 h-3 text-indigo-500" />
                      <span>{summaryData.ai_model || 'Gemini 2.0 Flash'} Synthesized</span>
                    </div>
                  ) : (
                    <div className="inline-flex items-center gap-1.5 bg-slate-100 border border-slate-300 text-slate-700 px-2.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider">
                      <span>Deterministic Rule Engine</span>
                    </div>
                  )}
                  {summaryData?.validation_status && (
                    <div className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border ${
                      summaryData.validation_status.includes('corrections')
                        ? 'bg-amber-50 border-amber-200 text-amber-800'
                        : 'bg-emerald-50 border-emerald-200 text-emerald-800'
                    }`}>
                      <ShieldCheck className="w-3 h-3" />
                      <span>{summaryData.validation_status.replace(/_/g, ' ')}</span>
                    </div>
                  )}
                </div>
                <h2 className="text-2xl sm:text-4xl font-black text-slate-900 mt-2 flex items-center gap-2">
                  <span>{summaryData?.topic_title || activeTopic || 'Public Opinion Summary'}</span>
                </h2>
                <p className="text-xs sm:text-sm text-slate-500 mt-1 font-normal">
                  Universal intelligence report synthesized across news reporting, multimedia, and public social commentary.
                </p>
              </div>

              {/* Action Controls */}
              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={() => handleSearch(activeTopic, true)}
                  disabled={loadingSearch}
                  className="inline-flex items-center gap-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs px-3.5 py-2.5 rounded-xl border border-slate-200 transition-colors cursor-pointer"
                  title="Force re-query of external providers"
                >
                  <RefreshCw className={`w-3.5 h-3.5 text-slate-500 ${loadingSearch ? 'animate-spin' : ''}`} />
                  <span>Refresh Topic Research</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setFormTopic(activeTopic);
                    setActiveTab('share');
                  }}
                  className="inline-flex items-center gap-1.5 bg-[#C8102E] hover:bg-[#A60C24] text-white font-bold text-xs px-4 py-2.5 rounded-xl shadow-xs transition-colors cursor-pointer"
                >
                  <Send className="w-3.5 h-3.5 text-amber-300" />
                  <span>Share an Opinion</span>
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('explore')}
                  className="inline-flex items-center gap-1.5 bg-white hover:bg-slate-50 text-slate-700 font-bold text-xs px-3.5 py-2.5 rounded-xl border border-slate-200 shadow-2xs transition-colors cursor-pointer"
                >
                  <Globe2 className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Explore Original Sources ({summaryData?.clean_sources?.length || publicRecords.length})</span>
                </button>
              </div>
            </div>

            {/* Top Section B: Overall Summary Synthesized Paragraphs */}
            <div className="p-5 sm:p-6 rounded-2xl bg-amber-50/40 border border-amber-200/80 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold text-amber-900 uppercase tracking-wider flex items-center gap-1.5">
                  <FileText className="w-3.5 h-3.5 text-[#C8102E]" />
                  Overall Summary & Public Consensus
                </span>
                <span className="text-[11px] text-slate-400">
                  Synthesized at {summaryData?.generated_at ? new Date(summaryData.generated_at).toLocaleTimeString() : 'Current'}
                </span>
              </div>
              <div className="text-xs sm:text-sm text-slate-800 leading-relaxed space-y-2 whitespace-pre-line font-medium">
                {summaryData?.overall_summary || 'No summary text available yet for this topic.'}
              </div>
            </div>

            {/* Top Section J: Coverage Status & Sample Limitations */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
              <div className="bg-white p-3.5 rounded-xl border border-slate-200 space-y-1">
                <span className="text-[10px] font-bold text-slate-500 uppercase block">Active Providers Searched</span>
                <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
                  {summaryData?.coverage?.provider_distribution && Object.keys(summaryData.coverage.provider_distribution).length > 0 ? (
                    Object.entries(summaryData.coverage.provider_distribution).map(([p, cnt]) => (
                      <span key={p} className="text-[11px] font-bold px-2 py-0.5 rounded-md bg-slate-100 text-slate-800 border border-slate-200 capitalize">
                        {p} ({cnt})
                      </span>
                    ))
                  ) : (
                    <span className="text-slate-400 text-[11px]">No active providers</span>
                  )}
                </div>
              </div>

              <div className="bg-white p-3.5 rounded-xl border border-slate-200 space-y-1">
                <span className="text-[10px] font-bold text-slate-500 uppercase block">Analyzed Unique Records</span>
                <div className="flex items-baseline gap-2">
                  <span className="text-xl font-black text-slate-900">
                    {summaryData?.coverage?.total_analyzed_records || 0}
                  </span>
                  <span className="text-[11px] text-slate-500">
                    sources ({citizenOpinionsCount} citizen voices)
                  </span>
                </div>
              </div>

              <div className="bg-white p-3.5 rounded-xl border border-slate-200 space-y-1">
                <span className="text-[10px] font-bold text-slate-500 uppercase block">Data Coverage Assessment</span>
                <p className="text-[11px] text-slate-600 leading-tight">
                  {summaryData?.sample_size_assessment || 'Standard public web commentary.'}
                </p>
              </div>
            </div>
          </div>

          {/* ========================================================================= */}
          {/* SECTION A: TOPIC INTRODUCTION                                             */}
          {/* ========================================================================= */}
          <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 shadow-xs space-y-4">
            <div className="flex items-center gap-2 text-xs font-bold text-[#C8102E] uppercase tracking-wider">
              <Sparkles className="w-4 h-4 text-[#C8102E]" />
              <span>Section A • Topic Introduction</span>
            </div>
            <h3 className="text-xl font-black text-slate-900">
              About &ldquo;{summaryData?.topic_title || activeTopic}&rdquo;
            </h3>
            <p className="text-xs sm:text-sm text-slate-700 leading-relaxed font-normal">
              {summaryData?.introduction || 'Information about this topic will appear once evidence is collected.'}
            </p>

            {summaryData?.relevant_dates && (
              <div className="p-3 rounded-xl bg-amber-50/70 border border-amber-200 text-xs text-amber-950 flex items-center gap-2 font-medium">
                <Info className="w-4 h-4 text-amber-700 shrink-0" />
                <span><strong>Event Background & Timeline:</strong> {summaryData.relevant_dates}</span>
              </div>
            )}

            {summaryData?.facts_vs_claims && (
              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-600 leading-relaxed">
                <span className="font-bold text-slate-800">Deterministic Distinction: </span>
                {summaryData.facts_vs_claims}
              </div>
            )}
          </div>

          {/* ========================================================================= */}
          {/* SECTION B: OVERALL SUMMARY (READABLE PARAGRAPHS & THEME HIGHLIGHTS)        */}
          {/* ========================================================================= */}
          <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 shadow-xs space-y-4">
            <div className="flex items-center gap-2 text-xs font-bold text-amber-800 uppercase tracking-wider">
              <FileText className="w-4 h-4 text-amber-600" />
              <span>Section B • Overall Summary</span>
            </div>
            <h3 className="text-xl font-black text-slate-900">
              Consolidated Public Opinion Synthesis
            </h3>
            <p className="text-xs text-slate-500">
              Synthesized collective perspective from retrieved sources without raw snippet concatenation.
            </p>

            <div className="p-5 rounded-2xl bg-amber-50/40 border border-amber-200/80 text-xs sm:text-sm text-slate-800 leading-relaxed space-y-3 whitespace-pre-line font-medium">
              {summaryData?.overall_summary || 'No summary synthesized.'}
            </div>

            {themes.length > 0 && (
              <div className="pt-2 space-y-2">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
                  Prominent Discussion Themes Identified:
                </span>
                <div className="flex flex-wrap gap-2">
                  {themes.map((th) => (
                    <span key={th.theme_id} className="text-xs font-semibold px-3 py-1 rounded-full bg-slate-100 border border-slate-200 text-slate-800 flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-[#C8102E]" />
                      {th.theme_label} ({th.record_count})
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* ========================================================================= */}
          {/* SECTION C: POSITIVE OPINIONS AND HIGHLIGHTS                                */}
          {/* ========================================================================= */}
          <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2 text-xs font-bold text-emerald-800 uppercase tracking-wider">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                <span>Section C • Positive Opinions & Highlights</span>
              </div>
              <span className="text-xs font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2.5 py-0.5 rounded-full">
                {summaryData?.positive_opinions?.length || 0} findings
              </span>
            </div>

            {(!summaryData?.positive_opinions || summaryData.positive_opinions.length === 0) ? (
              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 text-xs text-slate-600">
                {summaryData?.positive_opinions_status || 'No reliable positive opinions, appreciative highlights, or endorsements were found in the collected sources for this topic.'}
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {summaryData.positive_opinions.map((pos, idx) => (
                  <div key={idx} className="p-5 rounded-2xl bg-emerald-50/30 border border-emerald-200 space-y-3">
                    <div className="flex items-center justify-between gap-2">
                      <h4 className="font-bold text-slate-900 text-sm text-emerald-950">{pos.heading}</h4>
                      <div className="flex items-center gap-1.5 shrink-0">
                        {pos.evidence_strength && (
                          <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800 uppercase tracking-wider">
                            {pos.evidence_strength}
                          </span>
                        )}
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800">
                          {pos.supporting_evidence_count} {pos.supporting_evidence_count === 1 ? 'source' : 'sources'}
                        </span>
                      </div>
                    </div>
                    <p className="text-xs text-slate-700 leading-relaxed">{pos.explanation}</p>
                    {pos.source_urls && pos.source_urls.length > 0 && (
                      <div className="pt-2 border-t border-emerald-100 flex flex-wrap gap-2">
                        {pos.source_urls.map((url, uidx) => (
                          <a
                            key={uidx}
                            href={url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-[11px] font-semibold text-emerald-800 hover:text-emerald-950 hover:underline flex items-center gap-1 bg-white border border-emerald-200 px-2 py-0.5 rounded"
                          >
                            <span>Evidence #{uidx + 1}</span>
                            <ExternalLink className="w-2.5 h-2.5" />
                          </a>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* ========================================================================= */}
          {/* SECTION D: NEGATIVE OPINIONS AND CRITICISM                                */}
          {/* ========================================================================= */}
          <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2 text-xs font-bold text-red-800 uppercase tracking-wider">
                <AlertCircle className="w-4 h-4 text-[#C8102E]" />
                <span>Section D • Negative Opinions & Criticism</span>
              </div>
              <span className="text-xs font-bold text-red-700 bg-red-50 border border-red-200 px-2.5 py-0.5 rounded-full">
                {summaryData?.negative_opinions?.length || 0} criticisms
              </span>
            </div>

            {(!summaryData?.negative_opinions || summaryData.negative_opinions.length === 0) ? (
              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 text-xs text-slate-600">
                {summaryData?.negative_opinions_status || 'No critical, dissatisfied, or opposing viewpoints were identified in the collected evidence for this topic.'}
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {summaryData.negative_opinions.map((neg, idx) => (
                  <div key={idx} className="p-5 rounded-2xl bg-red-50/40 border border-red-200 space-y-3">
                    <div className="flex items-center justify-between gap-2">
                      <h4 className="font-bold text-slate-900 text-sm text-red-950">{neg.heading}</h4>
                      <div className="flex items-center gap-1.5 shrink-0">
                        {neg.evidence_strength && (
                          <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-red-100 text-red-800 uppercase tracking-wider">
                            {neg.evidence_strength}
                          </span>
                        )}
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-red-100 text-red-800">
                          {neg.supporting_evidence_count} {neg.supporting_evidence_count === 1 ? 'source' : 'sources'}
                        </span>
                      </div>
                    </div>
                    <p className="text-xs text-slate-700 leading-relaxed">{neg.explanation}</p>
                    {neg.source_urls && neg.source_urls.length > 0 && (
                      <div className="pt-2 border-t border-red-100 flex flex-wrap gap-2">
                        {neg.source_urls.map((url, uidx) => (
                          <a
                            key={uidx}
                            href={url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-[11px] font-semibold text-[#C8102E] hover:underline flex items-center gap-1 bg-white border border-red-200 px-2 py-0.5 rounded"
                          >
                            <span>Evidence #{uidx + 1}</span>
                            <ExternalLink className="w-2.5 h-2.5" />
                          </a>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* ========================================================================= */}
          {/* SECTION E: PROBLEMS AND CONCERNS                                          */}
          {/* ========================================================================= */}
          <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2 text-xs font-bold text-amber-900 uppercase tracking-wider">
                <Layers className="w-4 h-4 text-amber-600" />
                <span>Section E • Problems & Concerns</span>
              </div>
              <span className="text-xs font-bold text-slate-600 bg-slate-100 border border-slate-200 px-2.5 py-0.5 rounded-full">
                {summaryData?.problems_and_concerns?.length || 0} reported
              </span>
            </div>

            {(!summaryData?.problems_and_concerns || summaryData.problems_and_concerns.length === 0) ? (
              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 text-xs text-slate-600">
                {summaryData?.problems_and_concerns_status || 'No concrete operational hazards, acute service failures, or verified safety problems were reported in the analyzed records.'}
              </div>
            ) : (
              <div className="space-y-3">
                <p className="text-xs text-slate-500">
                  Identifies concrete problems and practical difficulties reported in the evidence:
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {summaryData.problems_and_concerns.map((prob, idx) => (
                    <div key={idx} className="p-4 rounded-2xl bg-slate-50 border border-slate-200 text-xs space-y-2">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-bold text-slate-900">{prob.heading}</span>
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-100 text-amber-900 capitalize border border-amber-200">
                          {prob.problem_type.replace('_', ' ')}
                        </span>
                      </div>
                      <p className="text-slate-600 leading-relaxed font-normal">{prob.description}</p>
                      {prob.source_urls && prob.source_urls.length > 0 && (
                        <div className="pt-1 flex gap-2">
                          <a href={prob.source_urls[0]} target="_blank" rel="noopener noreferrer" className="text-[10px] font-semibold text-[#C8102E] hover:underline flex items-center gap-0.5">
                            View Source Reference <ExternalLink className="w-2.5 h-2.5" />
                          </a>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* ========================================================================= */}
          {/* SECTION F: SUGGESTIONS AND PROPOSED IMPROVEMENTS                          */}
          {/* ========================================================================= */}
          <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2 text-xs font-bold text-amber-700 uppercase tracking-wider">
                <Lightbulb className="w-4 h-4 text-amber-500" />
                <span>Section F • Suggestions & Proposed Improvements</span>
              </div>
              <span className="text-xs font-bold text-slate-600 bg-slate-100 border border-slate-200 px-2.5 py-0.5 rounded-full">
                {summaryData?.suggestions_and_improvements?.length || 0} proposals
              </span>
            </div>

            {(!summaryData?.suggestions_and_improvements || summaryData.suggestions_and_improvements.length === 0) ? (
              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 text-xs text-slate-600">
                {summaryData?.suggestions_status || 'No specific improvement proposals or citizen recommendations were recorded in the retrieved sources.'}
              </div>
            ) : (
              <div className="space-y-3">
                <div className="text-[11px] text-slate-500 bg-amber-50/60 p-3 rounded-xl border border-amber-200">
                  <strong>Transparency Notice:</strong> Contributor suggestions are separated from algorithmic recommendations. CivicVoice never attributes synthesized recommendations to real persons.
                </div>
                <div className="space-y-3">
                  {summaryData.suggestions_and_improvements.map((sug, idx) => (
                    <div
                      key={idx}
                      className={`p-4 rounded-2xl border text-xs space-y-2 ${
                        sug.origin === 'source_author'
                          ? 'bg-white border-slate-200'
                          : 'bg-amber-50/40 border-amber-200'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase ${
                            sug.origin === 'source_author'
                              ? 'bg-blue-50 text-blue-800 border-blue-200'
                              : 'bg-purple-50 text-purple-800 border-purple-200'
                          }`}>
                            {sug.origin === 'source_author' ? 'Source Contributor Suggestion' : 'CivicVoice Synthesized Recommendation'}
                          </span>
                          <span className="font-bold text-slate-900">{sug.heading}</span>
                        </div>
                      </div>
                      <p className="text-slate-700 leading-relaxed font-medium">&ldquo;{sug.suggestion}&rdquo;</p>
                      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-1 pt-1 text-[10px] text-slate-400">
                        <span>{sug.disclaimer}</span>
                        {sug.source_url && (
                          <a href={sug.source_url} target="_blank" rel="noopener noreferrer" className="text-[#C8102E] hover:underline font-semibold flex items-center gap-0.5 shrink-0">
                            View Source Reference <ExternalLink className="w-2.5 h-2.5" />
                          </a>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* ========================================================================= */}
          {/* SECTION G: DIFFERENT VIEWPOINTS AND DISAGREEMENTS                         */}
          {/* ========================================================================= */}
          <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 shadow-xs space-y-4">
            <div className="flex items-center gap-2 text-xs font-bold text-slate-700 uppercase tracking-wider border-b border-slate-100 pb-3">
              <Layers className="w-4 h-4 text-slate-600" />
              <span>Section G • Different Viewpoints & Disagreements</span>
            </div>

            {(!summaryData?.viewpoint_contrasts || summaryData.viewpoint_contrasts.length === 0) ? (
              <p className="text-xs text-slate-500">Commentary across active sources reflects broadly uniform perspectives.</p>
            ) : (
              <div className="space-y-4">
                {summaryData.viewpoint_contrasts.map((vc, idx) => (
                  <div key={idx} className="p-5 rounded-2xl bg-slate-50 border border-slate-200 space-y-3 text-xs">
                    <h4 className="font-bold text-slate-900 text-sm">{vc.topic_aspect}</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <div className="p-3 bg-white rounded-xl border border-slate-200 space-y-1">
                        <span className="text-[10px] font-bold text-emerald-800 uppercase block">What People Agree On:</span>
                        <p className="text-slate-600 leading-relaxed font-medium">{vc.areas_of_agreement}</p>
                      </div>
                      <div className="p-3 bg-white rounded-xl border border-slate-200 space-y-1">
                        <span className="text-[10px] font-bold text-[#C8102E] uppercase block">Where Opinions Differ:</span>
                        <p className="text-slate-600 leading-relaxed font-medium">{vc.points_of_disagreement}</p>
                      </div>
                    </div>
                    {vc.disputed_questions && vc.disputed_questions.length > 0 && (
                      <div className="pt-2 border-t border-slate-200/80">
                        <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
                          Unresolved Disputed Questions:
                        </span>
                        <ul className="list-disc list-inside space-y-0.5 text-slate-600">
                          {vc.disputed_questions.map((dq, qidx) => (
                            <li key={qidx} className="text-[11px] font-medium">{dq}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {summaryData?.unresolved_questions && summaryData.unresolved_questions.length > 0 && (
              <div className="p-4 sm:p-5 rounded-2xl bg-amber-50/70 border border-amber-200/90 text-xs space-y-2 mt-4">
                <span className="font-bold text-amber-950 uppercase text-[10px] tracking-wider flex items-center gap-1.5">
                  <AlertCircle className="w-3.5 h-3.5 text-amber-700" />
                  Identified Evidence Gaps & Unresolved Questions
                </span>
                <ul className="list-disc list-inside space-y-1 text-slate-700">
                  {summaryData.unresolved_questions.map((uq, uidx) => (
                    <li key={uidx} className="font-medium">{uq}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* ========================================================================= */}
          {/* SECTION H: TRENDS AND CHANGES OVER TIME                                   */}
          {/* ========================================================================= */}
          <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2 text-xs font-bold text-emerald-800 uppercase tracking-wider">
                <TrendingUp className="w-4 h-4 text-emerald-600" />
                <span>Section H • Trends & Changes Over Time</span>
              </div>
              <span className="text-[11px] font-semibold text-slate-500">
                7-Day Successive Comparison
              </span>
            </div>

            <p className="text-xs sm:text-sm text-slate-700 leading-relaxed font-medium">
              {summaryData?.trends_overview || 'Trend analysis requires multiple dated entries across consecutive time windows.'}
            </p>

            {summaryData?.trend_items && summaryData.trend_items.length > 0 && (
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 pt-2">
                {summaryData.trend_items.map((tr) => (
                  <div key={tr.theme_id} className="p-3.5 rounded-xl border border-slate-200 bg-slate-50 text-xs space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-slate-900">{tr.theme_label}</span>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded capitalize ${
                        tr.status === 'emerging' || tr.status === 'surging'
                          ? 'bg-amber-100 text-amber-900'
                          : tr.status === 'declining'
                          ? 'bg-blue-50 text-blue-800'
                          : 'bg-slate-200 text-slate-700'
                      }`}>
                        {tr.status}
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-500">
                      Current window count: <strong>{tr.current_window_count}</strong> ({tr.change_count >= 0 ? `+${tr.change_count}` : tr.change_count})
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* ========================================================================= */}
          {/* SECTION I: EVIDENCE AND SOURCES (CLEAN, EXPANDABLE DEDUPLICATED LIST)      */}
          {/* ========================================================================= */}
          <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 shadow-xs space-y-4">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
              <div>
                <div className="flex items-center gap-2 text-xs font-bold text-slate-900 uppercase tracking-wider">
                  <Globe2 className="w-4 h-4 text-emerald-600" />
                  <span>Section I • Evidence & Original Sources</span>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  Deduplicated source list with publisher attribution, publication dates, and bounded evidence summaries.
                </p>
              </div>
              <span className="text-xs font-bold text-slate-700 bg-slate-100 border border-slate-200 px-2.5 py-0.5 rounded-full">
                {summaryData?.clean_sources?.length || 0} unique sources
              </span>
            </div>

            {(!summaryData?.clean_sources || summaryData.clean_sources.length === 0) ? (
              <p className="text-xs text-slate-400 py-4 text-center">No clean source records attached.</p>
            ) : (
              <div className="divide-y divide-slate-100">
                {summaryData.clean_sources.map((src, sidx) => (
                  <div key={sidx} className="py-4 space-y-2 text-xs">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-slate-900 text-xs px-2 py-0.5 rounded bg-slate-100 border border-slate-200">
                          {src.publisher}
                        </span>
                        <span className="text-[10px] font-semibold text-slate-600 bg-slate-50 border border-slate-200 px-2 py-0.5 rounded capitalize">
                          {src.source_type.replace('_', ' ')}
                        </span>
                        {src.language && (
                          <span className="text-[10px] text-slate-400">
                            lang: {src.language}
                          </span>
                        )}
                      </div>
                      <span className="text-[10px] text-slate-400 font-medium">
                        {src.published_at ? new Date(src.published_at).toLocaleDateString() : 'Date unavailable'}
                      </span>
                    </div>

                    <h5 className="font-bold text-slate-900 text-xs sm:text-sm">{src.title}</h5>
                    <p className="text-slate-600 leading-relaxed font-normal">
                      {src.excerpt}
                    </p>

                    <div className="flex items-center justify-between pt-1">
                      <span className="text-[10px] text-slate-400">External verified URL</span>
                      <a
                        href={src.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[#C8102E] hover:underline flex items-center gap-1 font-semibold text-[11px]"
                      >
                        Visit Original Link <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* ========================================================================= */}
          {/* SECTION J: DATA COVERAGE AND LIMITATIONS                                  */}
          {/* ========================================================================= */}
          <div className="bg-slate-50 border border-slate-200 rounded-3xl p-6 sm:p-8 text-xs space-y-4">
            <div className="flex items-center gap-2 text-xs font-bold text-slate-800 uppercase tracking-wider border-b border-slate-200 pb-3">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              <span>Section J • Data Coverage & Limitations</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="bg-white p-3.5 rounded-xl border border-slate-200 space-y-1">
                <span className="text-[10px] font-bold text-slate-500 uppercase block">Provider Coverage</span>
                {summaryData?.coverage?.provider_distribution &&
                  Object.entries(summaryData.coverage.provider_distribution).map(([p, c]) => (
                    <div key={p} className="flex justify-between text-[11px] text-slate-700">
                      <span className="capitalize">{p}:</span>
                      <span className="font-bold">{c} records</span>
                    </div>
                  ))}
              </div>

              <div className="bg-white p-3.5 rounded-xl border border-slate-200 space-y-1">
                <span className="text-[10px] font-bold text-slate-500 uppercase block">Language Breakdown</span>
                {summaryData?.coverage?.language_distribution &&
                  Object.entries(summaryData.coverage.language_distribution).map(([l, c]) => (
                    <div key={l} className="flex justify-between text-[11px] text-slate-700">
                      <span>{l === 'en' ? 'English' : l === 'kn' ? 'ಕನ್ನಡ (Kannada)' : l}:</span>
                      <span className="font-bold">{c} records</span>
                    </div>
                  ))}
              </div>

              <div className="bg-white p-3.5 rounded-xl border border-slate-200 space-y-1">
                <span className="text-[10px] font-bold text-slate-500 uppercase block">Timestamp Quality</span>
                <div className="text-[11px] text-slate-700 space-y-0.5">
                  <div>Missing publication timestamps: <strong>{summaryData?.coverage?.missing_timestamps_count || 0}</strong></div>
                  <div className="text-[10px] text-slate-400">Voluntary commentary basis</div>
                </div>
              </div>
            </div>

            <div className="space-y-1 text-slate-600 text-[11px] leading-relaxed pt-1">
              <span className="font-bold text-slate-800 block">Methodological Disclaimers:</span>
              {summaryData?.coverage?.limitations?.map((lim, idx) => (
                <p key={idx}>• {lim}</p>
              )) || (
                <>
                  <p>• Findings reflect public commentary collected across Bluesky, YouTube, and Tavily.</p>
                  <p>• Data does not represent an exhaustive census of all residents.</p>
                </>
              )}
            </div>
          </div>

          {/* ========================================================================= */}
          {/* BOTTOM ACTIONS BAR                                                        */}
          {/* ========================================================================= */}
          <div className="p-8 rounded-3xl bg-gradient-to-r from-red-50 via-white to-amber-50 border border-red-200 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="text-left space-y-1">
              <h4 className="font-bold text-slate-900 text-sm sm:text-base">Ready to explore more or contribute?</h4>
              <p className="text-xs text-slate-600">
                Explore individual records, share your community feedback, or research another civic topic.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => setActiveTab('explore')}
                className="bg-white hover:bg-slate-50 text-slate-800 font-bold text-xs px-4 py-2.5 rounded-xl border border-slate-200 shadow-2xs transition-colors cursor-pointer"
              >
                Explore Source Records
              </button>
              <button
                type="button"
                onClick={() => {
                  setFormTopic(activeTopic);
                  setActiveTab('share');
                }}
                className="bg-[#C8102E] hover:bg-[#A60C24] text-white font-bold text-xs px-4 py-2.5 rounded-xl shadow-xs transition-colors cursor-pointer"
              >
                Share an Opinion
              </button>
              <button
                type="button"
                onClick={() => {
                  window.scrollTo({ top: 0, behavior: 'smooth' });
                }}
                className="bg-amber-100 hover:bg-amber-200 text-amber-900 font-bold text-xs px-4 py-2.5 rounded-xl border border-amber-300/80 transition-colors cursor-pointer"
              >
                Search Another Topic
              </button>
            </div>
          </div>
        </section>
      )}

      {/* ========================================================================= */}
      {/* TAB 5: OFFICIAL VERIFIED CIVIC REPORTS (PROMPT 4)                         */}
      {/* ========================================================================= */}
      {activeTab === 'reports' && (
        <section className="space-y-6">
          {/* Action Notification Alert */}
          {actionNotice && (
            <div
              className={`p-4 rounded-2xl border flex items-start justify-between gap-3 text-sm animate-in fade-in duration-200 ${
                actionNotice.type === 'success'
                  ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
                  : actionNotice.type === 'error'
                  ? 'bg-rose-50 border-rose-200 text-rose-900'
                  : 'bg-amber-50 border-amber-200 text-amber-900'
              }`}
            >
              <div className="flex items-center gap-2">
                {actionNotice.type === 'success' && <CheckCircle className="w-5 h-5 text-emerald-600 shrink-0" />}
                {actionNotice.type === 'error' && <AlertCircle className="w-5 h-5 text-rose-600 shrink-0" />}
                {actionNotice.type === 'info' && <Info className="w-5 h-5 text-amber-600 shrink-0" />}
                <p className="font-medium leading-relaxed">{actionNotice.text}</p>
              </div>
              <button
                onClick={() => setActionNotice(null)}
                className="text-slate-400 hover:text-slate-700 text-xs font-bold px-2 py-1"
              >
                Dismiss
              </button>
            </div>
          )}

          {/* Reviewer Credential Ribbon */}
          <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-700">
                <Lock className="w-4 h-4 text-[#C8102E]" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
                  Authorized Reviewer Session
                  <span className="text-[10px] bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full font-semibold">
                    Protected Tier
                  </span>
                </h4>
                <p className="text-[11px] text-slate-500">
                  Privileged actions (generation, editing, approval, dispatch) are cryptographically audited.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 w-full sm:w-auto">
              <input
                type="password"
                placeholder="CIVICVOICE_API_TOKEN"
                value={reportsAuthToken}
                onChange={(e) => setReportsAuthToken(e.target.value)}
                className="text-xs bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-slate-800 w-full sm:w-56 focus:outline-hidden focus:ring-2 focus:ring-[#C8102E]/20"
                title="Reviewer authorization token"
              />
              <button
                onClick={fetchReports}
                disabled={loadingReports}
                className="px-3.5 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shrink-0 transition-colors"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loadingReports ? 'animate-spin' : ''}`} />
                <span>Sync</span>
              </button>
            </div>
          </div>

          {/* Main 2-Column Reports Interface */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            {/* Left Column: Generator & Report Catalog */}
            <div className="lg:col-span-5 space-y-6">
              {/* Generate New Brief Form Card */}
              <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-xs space-y-4">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-red-50 border border-red-200 flex items-center justify-center text-[#C8102E]">
                    <FileText className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-slate-900">Generate Official Civic Brief</h3>
                    <p className="text-[11px] text-slate-500">Synthesizes real analysis and citizen feedback</p>
                  </div>
                </div>

                <form onSubmit={handleGenerateReport} className="space-y-3 pt-2">
                  <div>
                    <label className="text-[11px] font-bold text-slate-700 block mb-1">Civic Topic</label>
                    <select
                      value={generateTopic}
                      onChange={(e) => setGenerateTopic(e.target.value)}
                      className="w-full text-xs bg-slate-50 border border-slate-200 rounded-xl p-2.5 text-slate-900 font-medium focus:ring-2 focus:ring-[#C8102E]/20"
                    >
                      <option value="roads_infrastructure">Roads & Potholes (BBMP Road Infrastructure)</option>
                      <option value="solid_waste">Waste & Sanitation (BBMP SWM / BSWML)</option>
                      <option value="water_drainage">Water Supply & Sewage (BWSSB 1916)</option>
                      <option value="electricity_lighting">Street Lighting & Power (BESCOM 1912)</option>
                      <option value="traffic_transit">Traffic & Public Transit (Bengaluru Traffic Police)</option>
                      <option value="parks_environment">Parks & Tree Management (BBMP Tree Cell)</option>
                      <option value="general_governance">General Civic / Unverified Authority</option>
                    </select>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="text-[11px] font-bold text-slate-700 block mb-1">Period (Days)</label>
                      <select
                        value={generatePeriodDays}
                        onChange={(e) => setGeneratePeriodDays(Number(e.target.value))}
                        className="w-full text-xs bg-slate-50 border border-slate-200 rounded-xl p-2.5 text-slate-900 font-medium"
                      >
                        <option value={7}>Last 7 Days</option>
                        <option value={14}>Last 14 Days</option>
                        <option value={30}>Last 30 Days</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-[11px] font-bold text-slate-700 block mb-1">Scope</label>
                      <input
                        type="text"
                        disabled
                        value="Bengaluru Urban"
                        className="w-full text-xs bg-slate-100 border border-slate-200 rounded-xl p-2.5 text-slate-600 font-medium"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="text-[11px] font-bold text-slate-700 block mb-1">
                      Custom Title <span className="text-slate-400 font-normal">(Optional)</span>
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. Q4 Monsoon Road Remediation Priority"
                      value={generateCustomTitle}
                      onChange={(e) => setGenerateCustomTitle(e.target.value)}
                      className="w-full text-xs bg-slate-50 border border-slate-200 rounded-xl p-2.5 text-slate-900 font-medium focus:ring-2 focus:ring-[#C8102E]/20"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={generatingReport}
                    className="w-full py-2.5 px-4 bg-[#C8102E] hover:bg-[#A00D24] text-white rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2 shadow-xs disabled:opacity-50"
                  >
                    {generatingReport ? (
                      <>
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        <span>Synthesizing Report...</span>
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-3.5 h-3.5" />
                        <span>Generate Draft Brief</span>
                      </>
                    )}
                  </button>
                </form>
              </div>

              {/* Reports Directory & Status Filter */}
              <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-xs space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
                    <FileText className="w-4 h-4 text-slate-600" />
                    <span>Report Registry</span>
                    <span className="text-[10px] bg-slate-100 text-slate-700 px-2 py-0.5 rounded-full font-bold">
                      {reportsList.length}
                    </span>
                  </h3>
                  <span className="text-[10px] text-slate-400">Deterministic Audit</span>
                </div>

                {/* Filter Pills */}
                <div className="flex flex-wrap gap-1">
                  {['all', 'draft', 'pending_review', 'approved', 'sent', 'rejected'].map((st) => (
                    <button
                      key={st}
                      onClick={() => setReportsFilterStatus(st)}
                      className={`text-[10px] font-bold px-2.5 py-1 rounded-lg capitalize transition-colors ${
                        reportsFilterStatus === st
                          ? 'bg-slate-900 text-white'
                          : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                      }`}
                    >
                      {st.replace('_', ' ')}
                    </button>
                  ))}
                </div>

                {/* List items */}
                {loadingReports ? (
                  <div className="py-8 text-center text-xs text-slate-400 flex items-center justify-center gap-2">
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Loading reports...</span>
                  </div>
                ) : reportsList.length === 0 ? (
                  <div className="py-8 text-center text-xs text-slate-500 bg-slate-50 rounded-2xl border border-dashed border-slate-200 p-4">
                    No reports match status &apos;{reportsFilterStatus}&apos;. Generate a new brief above.
                  </div>
                ) : (
                  <div className="space-y-2 max-h-[480px] overflow-y-auto pr-1">
                    {reportsList.map((rep) => {
                      const isSelected = selectedReport?.id === rep.id;
                      const statusColor =
                        rep.status === 'approved'
                          ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                          : rep.status === 'sent'
                          ? 'bg-blue-50 text-blue-700 border-blue-200'
                          : rep.status === 'rejected'
                          ? 'bg-rose-50 text-rose-700 border-rose-200'
                          : rep.status === 'pending_review'
                          ? 'bg-amber-50 text-amber-700 border-amber-200'
                          : 'bg-slate-100 text-slate-700 border-slate-200';

                      return (
                        <div
                          key={rep.id}
                          onClick={() => selectReport(rep)}
                          className={`p-3.5 rounded-2xl border cursor-pointer transition-all text-left space-y-2 ${
                            isSelected
                              ? 'bg-red-50/40 border-[#C8102E] shadow-xs ring-1 ring-[#C8102E]/20'
                              : 'bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50/50'
                          }`}
                        >
                          <div className="flex items-start justify-between gap-2">
                            <h4 className="text-xs font-bold text-slate-900 leading-snug line-clamp-1">
                              {rep.title}
                            </h4>
                            <span
                              className={`text-[9px] font-extrabold uppercase px-2 py-0.5 rounded border shrink-0 ${statusColor}`}
                            >
                              {rep.status.replace('_', ' ')}
                            </span>
                          </div>

                          <div className="text-[11px] text-slate-600 line-clamp-1 flex items-center gap-1.5">
                            <Building2 className="w-3 h-3 text-slate-400 shrink-0" />
                            <span>{rep.authority_name}</span>
                          </div>

                          <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1 border-t border-slate-100">
                            <span className="flex items-center gap-1 font-medium">
                              {rep.mapping_verified ? (
                                <span className="text-emerald-700 font-semibold flex items-center gap-0.5">
                                  <ShieldCheck className="w-3 h-3 text-emerald-600" /> Verified Dept
                                </span>
                              ) : (
                                <span className="text-amber-700 font-semibold flex items-center gap-0.5">
                                  <AlertCircle className="w-3 h-3 text-amber-600" /> Unverified
                                </span>
                              )}
                            </span>
                            <span>{new Date(rep.created_at).toLocaleDateString()}</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>

            {/* Right Column: Detailed Review, Edit, Approval & Dispatch */}
            <div className="lg:col-span-7">
              {!selectedReport ? (
                <div className="bg-white border border-slate-200 rounded-3xl p-12 text-center space-y-3 shadow-xs">
                  <div className="w-12 h-12 rounded-2xl bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-400 mx-auto">
                    <FileText className="w-6 h-6" />
                  </div>
                  <h3 className="text-base font-bold text-slate-900">Select or Generate a Report</h3>
                  <p className="text-xs text-slate-500 max-w-sm mx-auto leading-relaxed">
                    Choose an official brief from the registry on the left to inspect evidence, edit content, execute human review approval, or authorize government dispatch.
                  </p>
                </div>
              ) : (
                <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 shadow-xs space-y-6">
                  {/* Report Header Bar */}
                  <div className="space-y-3 pb-6 border-b border-slate-100">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div className="flex items-center gap-2">
                        <span
                          className={`text-xs font-black uppercase px-2.5 py-1 rounded-md border ${
                            selectedReport.status === 'approved'
                              ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                              : selectedReport.status === 'sent'
                              ? 'bg-blue-50 text-blue-700 border-blue-200'
                              : selectedReport.status === 'rejected'
                              ? 'bg-rose-50 text-rose-700 border-rose-200'
                              : selectedReport.status === 'pending_review'
                              ? 'bg-amber-50 text-amber-700 border-amber-200'
                              : 'bg-slate-100 text-slate-700 border-slate-200'
                          }`}
                        >
                          Status: {selectedReport.status.replace('_', ' ')}
                        </span>
                        <span className="text-[11px] font-mono bg-slate-100 text-slate-700 px-2 py-0.5 rounded border border-slate-200" title={`SHA-256 Digest: ${selectedReport.content_hash}`}>
                          Hash: {selectedReport.content_hash.slice(0, 10)}...
                        </span>
                      </div>

                      {/* Action Buttons Toolbar */}
                      <div className="flex flex-wrap items-center gap-2">
                        {!isEditingReport ? (
                          <>
                            <button
                              onClick={() => setIsEditingReport(true)}
                              className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-800 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-colors"
                            >
                              <Edit3 className="w-3.5 h-3.5" />
                              <span>Edit</span>
                            </button>

                            {selectedReport.status !== 'approved' && selectedReport.status !== 'sent' && (
                              <button
                                onClick={handleApproveReport}
                                disabled={approving}
                                className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-xs transition-colors disabled:opacity-50"
                              >
                                {approving ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle className="w-3.5 h-3.5" />}
                                <span>Approve</span>
                              </button>
                            )}

                            {selectedReport.status !== 'rejected' && selectedReport.status !== 'sent' && (
                              <button
                                onClick={() => setShowRejectModal(true)}
                                className="px-3 py-1.5 bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-colors"
                              >
                                <XCircle className="w-3.5 h-3.5" />
                                <span>Reject</span>
                              </button>
                            )}

                            <button
                              onClick={handleExportReport}
                              disabled={exporting}
                              className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-colors"
                            >
                              <FileDown className="w-3.5 h-3.5" />
                              <span>Export</span>
                            </button>

                            {selectedReport.status === 'approved' && (
                              <button
                                onClick={() => setShowSendModal(true)}
                                className="px-4 py-1.5 bg-[#C8102E] hover:bg-[#A00D24] text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-xs transition-colors"
                              >
                                <Mail className="w-3.5 h-3.5" />
                                <span>Authorize Send</span>
                              </button>
                            )}
                          </>
                        ) : (
                          <>
                            <button
                              onClick={() => setIsEditingReport(false)}
                              className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-bold transition-colors"
                            >
                              Cancel
                            </button>
                            <button
                              onClick={handleSaveEdit}
                              disabled={savingEdit}
                              className="px-4 py-1.5 bg-[#C8102E] hover:bg-[#A00D24] text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-xs transition-colors disabled:opacity-50"
                            >
                              {savingEdit ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                              <span>Save Edits</span>
                            </button>
                          </>
                        )}
                      </div>
                    </div>

                    {/* Invalidation Alert if in edit mode */}
                    {isEditingReport && (
                      <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-900 flex items-center gap-2">
                        <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
                        <span>
                          <strong>Review Integrity Rule:</strong> Saving changes will alter the content hash and immediately invalidate any prior approval, returning the report to pending review.
                        </span>
                      </div>
                    )}

                    {/* Report Title */}
                    {isEditingReport ? (
                      <div>
                        <label className="text-[11px] font-bold text-slate-700 block mb-1">Report Title</label>
                        <input
                          type="text"
                          value={editTitle}
                          onChange={(e) => setEditTitle(e.target.value)}
                          className="w-full text-base font-bold bg-slate-50 border border-slate-300 rounded-xl p-2.5 text-slate-900"
                        />
                      </div>
                    ) : (
                      <h2 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight leading-snug">
                        {selectedReport.title}
                      </h2>
                    )}

                    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500">
                      <span>Ref ID: <code className="text-slate-700 font-mono text-[11px]">{selectedReport.id.slice(0, 12)}...</code></span>
                      <span>Scope: <strong className="text-slate-800">{selectedReport.geographic_scope}</strong></span>
                      {selectedReport.approved_by && (
                        <span className="text-emerald-700 font-medium">Approved by: {selectedReport.approved_by}</span>
                      )}
                      {selectedReport.sent_at && (
                        <span className="text-blue-700 font-medium">Dispatched on: {new Date(selectedReport.sent_at).toLocaleString()}</span>
                      )}
                    </div>
                  </div>

                  {/* Responsible Government Authority Verification Card */}
                  <div className="bg-slate-50/70 border border-slate-200 rounded-2xl p-4 sm:p-5 space-y-3">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
                        <Building2 className="w-4 h-4 text-[#C8102E]" />
                        <span>Responsible Official Department</span>
                      </h4>
                      {selectedReport.mapping_verified ? (
                        <span className="text-[10px] font-extrabold bg-emerald-100 text-emerald-800 px-2.5 py-0.5 rounded-full flex items-center gap-1 border border-emerald-200">
                          <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                          Verified Official Channel
                        </span>
                      ) : (
                        <span className="text-[10px] font-extrabold bg-amber-100 text-amber-800 px-2.5 py-0.5 rounded-full flex items-center gap-1 border border-amber-200">
                          <AlertCircle className="w-3.5 h-3.5 text-amber-600" />
                          Unverified Authority — Review Required
                        </span>
                      )}
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                      <div>
                        <span className="text-slate-400 block text-[10px] font-semibold">Government Authority</span>
                        <span className="text-slate-900 font-bold">{selectedReport.authority_name}</span>
                        <span className="text-slate-500 block text-[11px]">{selectedReport.department_name}</span>
                      </div>

                      <div>
                        <span className="text-slate-400 block text-[10px] font-semibold">Official Contact / Channel</span>
                        {isEditingReport ? (
                          <input
                            type="email"
                            placeholder="officer@bbmp.gov.in"
                            value={editRecipientEmail}
                            onChange={(e) => setEditRecipientEmail(e.target.value)}
                            className="w-full text-xs bg-white border border-slate-300 rounded-lg p-1.5 mt-0.5 text-slate-800"
                          />
                        ) : (
                          <span className="text-slate-800 font-mono text-[11px] block">
                            {selectedReport.recipient_email || 'Unassigned — Manual review required'}
                          </span>
                        )}
                        {selectedReport.official_portal_url && (
                          <a
                            href={selectedReport.official_portal_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-[#C8102E] hover:underline text-[11px] flex items-center gap-1 mt-0.5"
                          >
                            <span>Official Portal</span>
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        )}
                      </div>
                    </div>

                    {selectedReport.mapping_source_url && (
                      <div className="pt-2 border-t border-slate-200/80 text-[10px] text-slate-500 flex flex-wrap items-center justify-between gap-2">
                        <span className="truncate max-w-sm">
                          Verification Source: <a href={selectedReport.mapping_source_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">{selectedReport.mapping_source_url}</a>
                        </span>
                        {selectedReport.mapping_last_verified && (
                          <span>Verified: {new Date(selectedReport.mapping_last_verified).toLocaleDateString()}</span>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Citizen Privacy & Sample Size Safeguards */}
                  <div className="bg-emerald-50/40 border border-emerald-200/80 rounded-2xl p-4 text-xs space-y-2">
                    <div className="flex items-center gap-2 text-emerald-900 font-bold">
                      <ShieldCheck className="w-4 h-4 text-emerald-600" />
                      <span>Citizen Privacy & Aggregate Safety Standards</span>
                    </div>
                    <p className="text-[11px] text-emerald-800/90 leading-relaxed">
                      Citizen submissions are protected under <strong>k-anonymity (minimum group threshold: 3)</strong>. Individual names, phone numbers, raw submission texts, and precise timestamps are strictly excluded from this report to prevent re-identification.
                    </p>
                    <div className="flex flex-wrap gap-4 pt-1 text-[11px] text-slate-700">
                      <span>Public Source Evidence: <strong>{selectedReport.source_records_count} records</strong></span>
                      <span>Represented Resident Voices: <strong>{selectedReport.citizen_submissions_count} submissions</strong></span>
                    </div>
                  </div>

                  {/* Report Executive Summary */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                        Executive Summary & Observed Civic Evidence
                      </h4>
                      {isEditingReport && <span className="text-[10px] text-slate-400">Markdown formatting supported</span>}
                    </div>

                    {isEditingReport ? (
                      <textarea
                        rows={10}
                        value={editSummary}
                        onChange={(e) => setEditSummary(e.target.value)}
                        className="w-full text-xs font-mono bg-slate-50 border border-slate-300 rounded-xl p-3 text-slate-900 leading-relaxed focus:ring-2 focus:ring-[#C8102E]/20"
                      />
                    ) : (
                      <div className="prose prose-xs max-w-none bg-slate-50/50 border border-slate-200 rounded-2xl p-5 text-slate-800 text-xs leading-relaxed whitespace-pre-line">
                        {selectedReport.summary_content}
                      </div>
                    )}
                  </div>

                  {/* Recommended Administrative Actions */}
                  <div className="space-y-2">
                    <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                      <Lightbulb className="w-4 h-4 text-amber-500" />
                      <span>Recommended Official Actions</span>
                    </h4>

                    {isEditingReport ? (
                      <textarea
                        rows={5}
                        value={editRecommendations}
                        onChange={(e) => setEditRecommendations(e.target.value)}
                        className="w-full text-xs font-mono bg-slate-50 border border-slate-300 rounded-xl p-3 text-slate-900 leading-relaxed focus:ring-2 focus:ring-[#C8102E]/20"
                      />
                    ) : (
                      <div className="bg-amber-50/30 border border-amber-200/80 rounded-2xl p-4 text-slate-800 text-xs leading-relaxed whitespace-pre-line">
                        {selectedReport.recommendations}
                      </div>
                    )}
                  </div>

                  {/* Limitations and Disclaimers */}
                  <div className="space-y-2">
                    <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                      <AlertCircle className="w-3.5 h-3.5 text-slate-500" />
                      <span>Methodology Limitations & Privacy Notice</span>
                    </h4>

                    {isEditingReport ? (
                      <textarea
                        rows={4}
                        value={editLimitations}
                        onChange={(e) => setEditLimitations(e.target.value)}
                        className="w-full text-xs font-mono bg-slate-50 border border-slate-300 rounded-xl p-3 text-slate-900 leading-relaxed focus:ring-2 focus:ring-[#C8102E]/20"
                      />
                    ) : (
                      <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4 text-slate-600 text-[11px] leading-relaxed whitespace-pre-line">
                        {selectedReport.limitations}
                      </div>
                    )}
                  </div>

                  {/* Original Public Evidence Links */}
                  {selectedReport.evidence_urls && selectedReport.evidence_urls.length > 0 && (
                    <div className="space-y-2 pt-2">
                      <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                        <ExternalLink className="w-3.5 h-3.5 text-[#C8102E]" />
                        <span>Supporting Public Source Evidence Links ({selectedReport.evidence_urls.length})</span>
                      </h4>
                      <div className="flex flex-wrap gap-2 text-xs">
                        {selectedReport.evidence_urls.map((url, i) => (
                          <a
                            key={i}
                            href={url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="bg-slate-50 hover:bg-slate-100 border border-slate-200 px-3 py-1.5 rounded-xl text-slate-700 font-medium flex items-center gap-1.5 text-[11px] transition-colors"
                          >
                            <ExternalLink className="w-3 h-3 text-slate-400" />
                            <span className="truncate max-w-[240px]">{url}</span>
                          </a>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Governance & Audit Trail Log */}
                  {selectedReport.audits && selectedReport.audits.length > 0 && (
                    <div className="space-y-2 pt-4 border-t border-slate-100">
                      <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                        <History className="w-3.5 h-3.5 text-slate-500" />
                        <span>Audit Trail & Human Review Log</span>
                      </h4>
                      <div className="space-y-1.5">
                        {selectedReport.audits.map((aud) => (
                          <div
                            key={aud.id}
                            className="text-[11px] bg-slate-50 border border-slate-200/80 rounded-xl p-2.5 flex flex-col sm:flex-row sm:items-center justify-between gap-1 text-slate-600"
                          >
                            <div className="flex items-center gap-2">
                              <span className="font-extrabold uppercase text-[10px] bg-white px-2 py-0.5 rounded border border-slate-200 text-slate-800">
                                {aud.action.replace('_', ' ')}
                              </span>
                              <span className="font-medium text-slate-800">{aud.performed_by}</span>
                              {aud.previous_status && aud.new_status && (
                                <span className="text-slate-400 text-[10px]">
                                  ({aud.previous_status} → {aud.new_status})
                                </span>
                              )}
                            </div>
                            <span className="text-[10px] text-slate-400">
                              {new Date(aud.created_at).toLocaleString()}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Rejection Modal */}
          {showRejectModal && (
            <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
              <div className="bg-white rounded-3xl border border-slate-200 p-6 max-w-md w-full space-y-4 shadow-xl animate-in zoom-in-95">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-rose-50 border border-rose-200 flex items-center justify-center text-rose-600">
                    <XCircle className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-slate-900">Reject Civic Report</h3>
                    <p className="text-xs text-slate-500">Provide specific justification for the audit trail</p>
                  </div>
                </div>

                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">Rejection Reason</label>
                  <textarea
                    rows={4}
                    placeholder="e.g. Sample size insufficient; re-run Tavily collector for Whitefield before official sign-off."
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                    className="w-full text-xs bg-slate-50 border border-slate-200 rounded-xl p-3 text-slate-900 focus:ring-2 focus:ring-rose-400"
                  />
                </div>

                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    onClick={() => setShowRejectModal(false)}
                    className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-bold transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleRejectReport}
                    disabled={rejecting || !rejectReason.trim()}
                    className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-xl text-xs font-bold transition-colors disabled:opacity-50"
                  >
                    {rejecting ? 'Rejecting...' : 'Confirm Rejection'}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Send Confirmation Modal */}
          {showSendModal && selectedReport && (
            <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
              <div className="bg-white rounded-3xl border border-slate-200 p-6 sm:p-8 max-w-lg w-full space-y-4 shadow-xl animate-in zoom-in-95">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-red-50 border border-red-200 flex items-center justify-center text-[#C8102E]">
                    <Mail className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-slate-900">Authorize Official Report Dispatch</h3>
                    <p className="text-xs text-slate-500">Explicit human confirmation required</p>
                  </div>
                </div>

                <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4 space-y-2 text-xs">
                  <div>
                    <span className="text-slate-400 text-[10px] block font-semibold">Report Reference</span>
                    <span className="font-bold text-slate-900">{selectedReport.title}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 text-[10px] block font-semibold">Official Recipient Channel</span>
                    <span className="font-mono text-slate-800 text-[11px] block">{selectedReport.recipient_email}</span>
                    <span className="text-slate-600 font-medium">{selectedReport.authority_name}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 text-[10px] block font-semibold">Cryptographic Digest Binding</span>
                    <span className="font-mono text-[10px] text-slate-700">{selectedReport.content_hash}</span>
                  </div>
                </div>

                <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-[11px] text-amber-900 leading-relaxed">
                  <strong>Important:</strong> If Resend email provider credentials are not configured in this environment, the workflow will verify and lock the approval and provide export files honestly without claiming false delivery.
                </div>

                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    onClick={() => setShowSendModal(false)}
                    className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-bold transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSendReport}
                    disabled={sending}
                    className="px-5 py-2 bg-[#C8102E] hover:bg-[#A00D24] text-white rounded-xl text-xs font-bold transition-colors flex items-center gap-2 shadow-xs disabled:opacity-50"
                  >
                    {sending ? (
                      <>
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        <span>Dispatching...</span>
                      </>
                    ) : (
                      <>
                        <Mail className="w-3.5 h-3.5" />
                        <span>Confirm & Dispatch</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Export View Modal */}
          {exportModalContent && (
            <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
              <div className="bg-white rounded-3xl border border-slate-200 p-6 sm:p-8 max-w-3xl w-full space-y-4 shadow-xl max-h-[90vh] flex flex-col animate-in zoom-in-95">
                <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                  <div className="flex items-center gap-2">
                    <FileDown className="w-5 h-5 text-slate-700" />
                    <h3 className="text-base font-bold text-slate-900">Exported Official Civic Report</h3>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(exportModalContent);
                        setCopiedExport(true);
                        setTimeout(() => setCopiedExport(false), 2000);
                      }}
                      className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-800 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-colors"
                    >
                      <Copy className="w-3.5 h-3.5" />
                      <span>{copiedExport ? 'Copied!' : 'Copy Markdown'}</span>
                    </button>
                    <button
                      onClick={() => setExportModalContent(null)}
                      className="px-3 py-1.5 bg-slate-900 text-white rounded-xl text-xs font-bold hover:bg-slate-800 transition-colors"
                    >
                      Close
                    </button>
                  </div>
                </div>

                <div className="overflow-y-auto flex-1 bg-slate-50 border border-slate-200 rounded-2xl p-4">
                  <pre className="text-xs font-mono text-slate-800 whitespace-pre-wrap leading-relaxed">
                    {exportModalContent}
                  </pre>
                </div>
              </div>
            </div>
          )}
        </section>
      )}
    </main>
  );
}

