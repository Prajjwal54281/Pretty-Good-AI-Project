import { useEffect, useState, useCallback } from "react";
import "@/App.css";
import axios from "axios";
import { Phone, Bug, FileText, Play, AlertTriangle, CheckCircle, Clock, RefreshCw, Trash2, Zap, AlertCircle, Info } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [scenarios, setScenarios] = useState([]);
  const [calls, setCalls] = useState([]);
  const [bugs, setBugs] = useState([]);
  const [selectedScenario, setSelectedScenario] = useState("");
  const [activeTab, setActiveTab] = useState("dashboard");
  const [selectedCall, setSelectedCall] = useState(null);
  const [configStatus, setConfigStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [callLoading, setCallLoading] = useState(false);
  
  // Bug report form
  const [bugForm, setBugForm] = useState({
    call_id: "",
    bug_description: "",
    severity: "medium",
    timestamp_in_call: "",
    details: "",
    recommendation: ""
  });

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [scenariosRes, callsRes, bugsRes, configRes] = await Promise.all([
        axios.get(`${API}/scenarios`),
        axios.get(`${API}/calls`),
        axios.get(`${API}/bugs`),
        axios.get(`${API}/config/status`)
      ]);
      setScenarios(scenariosRes.data.scenarios || []);
      setCalls(callsRes.data.calls || []);
      setBugs(bugsRes.data.bugs || []);
      setConfigStatus(configRes.data);
    } catch (e) {
      console.error("Error fetching data:", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const initiateCall = async () => {
    try {
      setCallLoading(true);
      const response = await axios.post(`${API}/call`, {
        scenario_name: selectedScenario || null
      });
      alert(`Call initiated! Call ID: ${response.data.call_id}\nScenario: ${response.data.scenario}`);
      setTimeout(fetchData, 2000);
    } catch (e) {
      alert(`Error: ${e.response?.data?.detail || e.message}`);
    } finally {
      setCallLoading(false);
    }
  };

  const submitBugReport = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/bugs`, bugForm);
      alert("Bug report submitted!");
      setBugForm({
        call_id: "",
        bug_description: "",
        severity: "medium",
        timestamp_in_call: "",
        details: "",
        recommendation: ""
      });
      fetchData();
    } catch (e) {
      alert(`Error: ${e.response?.data?.detail || e.message}`);
    }
  };

  const deleteBug = async (bugId) => {
    if (window.confirm("Delete this bug report?")) {
      try {
        await axios.delete(`${API}/bugs/${bugId}`);
        fetchData();
      } catch (e) {
        alert(`Error: ${e.response?.data?.detail || e.message}`);
      }
    }
  };

  const getSeverityColor = (severity) => {
    switch (severity) {
      case "critical": return "text-red-300 bg-red-950 border-red-800";
      case "high": return "text-orange-300 bg-orange-950 border-orange-800";
      case "medium": return "text-yellow-300 bg-yellow-950 border-yellow-800";
      case "low": return "text-green-300 bg-green-950 border-green-800";
      default: return "text-gray-400 bg-gray-800 border-gray-700";
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case "completed": return "text-emerald-400";
      case "in-progress": return "text-blue-400";
      case "initiated": return "text-yellow-400";
      case "failed": return "text-red-400";
      default: return "text-gray-400";
    }
  };

  const getScenarioCategory = (name) => {
    if (name.includes("Edge Case") || name.includes("Trap") || name.includes("Probe") || name.includes("Guardrail")) {
      return { label: "Edge Case", color: "text-purple-400 bg-purple-950" };
    }
    if (name.includes("Urgent") || name.includes("Human")) {
      return { label: "Escalation", color: "text-red-400 bg-red-950" };
    }
    return { label: "Standard", color: "text-cyan-400 bg-cyan-950" };
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-900/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-xl flex items-center justify-center">
                <Phone className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold tracking-tight">PGA Voice Bot</h1>
                <p className="text-xs text-slate-500">Athena AI Agent Tester</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className={`px-3 py-1 rounded-full text-xs font-medium ${configStatus?.vapi_configured ? 'bg-emerald-950 text-emerald-400' : 'bg-red-950 text-red-400'}`}>
                Vapi: {configStatus?.vapi_configured ? 'Ready' : 'Not Configured'}
              </span>
              <button 
                onClick={fetchData}
                data-testid="refresh-btn"
                className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 transition-colors"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <nav className="border-b border-slate-800 bg-slate-900/30">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex gap-1">
            {[
              { id: "dashboard", label: "Dashboard", icon: Phone },
              { id: "transcripts", label: "Transcripts", icon: FileText },
              { id: "bugs", label: "Bug Reports", icon: Bug, count: bugs.length },
            ].map((tab) => (
              <button
                key={tab.id}
                data-testid={`tab-${tab.id}`}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-3 text-sm font-medium transition-colors border-b-2 -mb-px ${
                  activeTab === tab.id
                    ? "border-cyan-500 text-cyan-400"
                    : "border-transparent text-slate-400 hover:text-slate-200"
                }`}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
                {tab.count > 0 && (
                  <span className="px-1.5 py-0.5 text-xs bg-red-600 text-white rounded-full">{tab.count}</span>
                )}
              </button>
            ))}
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Dashboard Tab */}
        {activeTab === "dashboard" && (
          <div className="space-y-8">
            {/* Call Control Panel */}
            <div className="bg-slate-900 rounded-2xl border border-slate-800 p-6">
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <Phone className="w-5 h-5 text-cyan-400" />
                Initiate Test Call to Athena
              </h2>
              <div className="grid md:grid-cols-3 gap-4">
                <div className="md:col-span-2">
                  <label className="block text-sm text-slate-400 mb-2">Select Test Scenario</label>
                  <select
                    data-testid="scenario-select"
                    value={selectedScenario}
                    onChange={(e) => setSelectedScenario(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 text-slate-100 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                  >
                    <option value="">Random Scenario</option>
                    {scenarios.map((s, i) => (
                      <option key={i} value={s.name}>{s.name}</option>
                    ))}
                  </select>
                </div>
                <div className="flex items-end">
                  <button
                    data-testid="initiate-call-btn"
                    onClick={initiateCall}
                    disabled={callLoading || !configStatus?.vapi_configured}
                    className="w-full bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 disabled:from-slate-700 disabled:to-slate-700 disabled:cursor-not-allowed text-white font-medium px-6 py-3 rounded-lg transition-all flex items-center justify-center gap-2"
                  >
                    {callLoading ? (
                      <RefreshCw className="w-5 h-5 animate-spin" />
                    ) : (
                      <Play className="w-5 h-5" />
                    )}
                    {callLoading ? "Calling..." : "Start Call"}
                  </button>
                </div>
              </div>
              <p className="text-xs text-slate-500 mt-3">
                Target: {configStatus?.target_number} | Via Vapi
              </p>
            </div>

            {/* Scenario Cards */}
            <div>
              <h2 className="text-lg font-semibold mb-4">Test Scenarios ({scenarios.length})</h2>
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                {scenarios.map((scenario, i) => {
                  const category = getScenarioCategory(scenario.name);
                  return (
                    <div
                      key={i}
                      data-testid={`scenario-card-${i}`}
                      onClick={() => setSelectedScenario(scenario.name)}
                      className={`bg-slate-900 border rounded-xl p-4 cursor-pointer transition-all hover:border-cyan-600 ${
                        selectedScenario === scenario.name ? "border-cyan-500 ring-1 ring-cyan-500/20" : "border-slate-800"
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <h3 className="font-medium text-slate-100 text-sm">{scenario.name}</h3>
                        <span className={`px-2 py-0.5 rounded text-xs ${category.color}`}>{category.label}</span>
                      </div>
                      <p className="text-xs text-slate-400 mb-2">{scenario.persona}</p>
                      <p className="text-xs text-slate-500">Goal: {scenario.goal}</p>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Recent Calls */}
            <div>
              <h2 className="text-lg font-semibold mb-4">Recent Calls</h2>
              <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
                <table className="w-full">
                  <thead className="bg-slate-800/50">
                    <tr>
                      <th className="text-left px-4 py-3 text-sm font-medium text-slate-400">Scenario</th>
                      <th className="text-left px-4 py-3 text-sm font-medium text-slate-400">Status</th>
                      <th className="text-left px-4 py-3 text-sm font-medium text-slate-400">Duration</th>
                      <th className="text-left px-4 py-3 text-sm font-medium text-slate-400">Auto Bugs</th>
                      <th className="text-left px-4 py-3 text-sm font-medium text-slate-400">Time</th>
                      <th className="text-left px-4 py-3 text-sm font-medium text-slate-400">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {calls.length === 0 ? (
                      <tr>
                        <td colSpan="6" className="px-4 py-8 text-center text-slate-500">
                          No calls yet. Start a test call above.
                        </td>
                      </tr>
                    ) : (
                      calls.slice(0, 10).map((call) => (
                        <tr key={call.id} className="hover:bg-slate-800/30" data-testid={`call-row-${call.id}`}>
                          <td className="px-4 py-3 text-sm">{call.scenario_name}</td>
                          <td className={`px-4 py-3 text-sm ${getStatusColor(call.status)}`}>
                            {call.status}
                          </td>
                          <td className="px-4 py-3 text-sm text-slate-400">
                            {call.duration_seconds ? `${call.duration_seconds}s` : "-"}
                          </td>
                          <td className="px-4 py-3 text-sm">
                            {(call.auto_detected_bugs?.length > 0) ? (
                              <span className="flex items-center gap-1 text-red-400">
                                <Zap className="w-3 h-3" />
                                {call.auto_detected_bugs.length}
                              </span>
                            ) : (
                              <span className="text-slate-600">-</span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-sm text-slate-500">
                            {new Date(call.started_at).toLocaleString()}
                          </td>
                          <td className="px-4 py-3">
                            <button
                              data-testid={`view-transcript-${call.id}`}
                              onClick={() => {
                                setSelectedCall(call);
                                setActiveTab("transcripts");
                              }}
                              className="text-cyan-400 hover:text-cyan-300 text-sm"
                            >
                              View
                            </button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Stats */}
            <div className="grid md:grid-cols-4 gap-4">
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-cyan-950 rounded-lg">
                    <Phone className="w-5 h-5 text-cyan-400" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{calls.length}</p>
                    <p className="text-xs text-slate-500">Total Calls</p>
                  </div>
                </div>
              </div>
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-emerald-950 rounded-lg">
                    <CheckCircle className="w-5 h-5 text-emerald-400" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{calls.filter(c => c.status === 'completed').length}</p>
                    <p className="text-xs text-slate-500">Completed</p>
                  </div>
                </div>
              </div>
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-red-950 rounded-lg">
                    <Bug className="w-5 h-5 text-red-400" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{bugs.length}</p>
                    <p className="text-xs text-slate-500">Bugs Found</p>
                  </div>
                </div>
              </div>
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-orange-950 rounded-lg">
                    <AlertTriangle className="w-5 h-5 text-orange-400" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{bugs.filter(b => b.severity === 'critical' || b.severity === 'high').length}</p>
                    <p className="text-xs text-slate-500">Critical/High</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Transcripts Tab */}
        {activeTab === "transcripts" && (
          <div className="grid lg:grid-cols-3 gap-6">
            {/* Call List */}
            <div className="lg:col-span-1">
              <h2 className="text-lg font-semibold mb-4">Call History</h2>
              <div className="space-y-2 max-h-[calc(100vh-250px)] overflow-y-auto">
                {calls.map((call) => (
                  <div
                    key={call.id}
                    data-testid={`transcript-item-${call.id}`}
                    onClick={() => setSelectedCall(call)}
                    className={`bg-slate-900 border rounded-lg p-3 cursor-pointer transition-all hover:border-cyan-600 ${
                      selectedCall?.id === call.id ? "border-cyan-500" : "border-slate-800"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-medium text-sm truncate">{call.scenario_name}</span>
                      <div className="flex items-center gap-2">
                        {call.auto_detected_bugs?.length > 0 && (
                          <span className="text-red-400 text-xs flex items-center gap-1">
                            <Zap className="w-3 h-3" />
                            {call.auto_detected_bugs.length}
                          </span>
                        )}
                        <span className={`text-xs ${getStatusColor(call.status)}`}>{call.status}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-slate-500">
                      <Clock className="w-3 h-3" />
                      {new Date(call.started_at).toLocaleDateString()}
                      {call.duration_seconds && ` • ${call.duration_seconds}s`}
                    </div>
                  </div>
                ))}
                {calls.length === 0 && (
                  <p className="text-slate-500 text-sm text-center py-8">No calls recorded yet.</p>
                )}
              </div>
            </div>

            {/* Transcript View */}
            <div className="lg:col-span-2">
              <h2 className="text-lg font-semibold mb-4">Transcript</h2>
              {selectedCall ? (
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                  <div className="mb-4 pb-4 border-b border-slate-800">
                    <div className="flex items-center justify-between">
                      <h3 className="font-medium">{selectedCall.scenario_name}</h3>
                      {selectedCall.auto_detected_bugs?.length > 0 && (
                        <span className="px-2 py-1 bg-red-950 text-red-400 text-xs rounded flex items-center gap-1">
                          <Zap className="w-3 h-3" />
                          {selectedCall.auto_detected_bugs.length} auto-detected issues
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-slate-400">{selectedCall.persona}</p>
                    <p className="text-xs text-slate-500">Goal: {selectedCall.goal}</p>
                  </div>
                  
                  {/* Auto-detected bugs alert */}
                  {selectedCall.auto_detected_bugs?.length > 0 && (
                    <div className="mb-4 p-3 bg-red-950/30 border border-red-900/50 rounded-lg">
                      <h4 className="text-sm font-medium text-red-400 flex items-center gap-2 mb-2">
                        <AlertCircle className="w-4 h-4" />
                        Auto-Detected Issues
                      </h4>
                      <ul className="space-y-1">
                        {selectedCall.auto_detected_bugs.map((bug, i) => (
                          <li key={i} className="text-xs text-red-300">• {bug.name}: {bug.description}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  
                  <div className="space-y-3 max-h-[calc(100vh-500px)] overflow-y-auto">
                    {selectedCall.transcript && selectedCall.transcript.length > 0 ? (
                      selectedCall.transcript.map((entry, i) => (
                        <div
                          key={i}
                          data-testid={`transcript-entry-${i}`}
                          className={`p-3 rounded-lg ${
                            entry.speaker === "patient"
                              ? "bg-cyan-950/30 border border-cyan-900/50 ml-0 mr-8"
                              : "bg-slate-800/50 border border-slate-700/50 ml-8 mr-0"
                          }`}
                        >
                          <span className={`text-xs font-medium ${
                            entry.speaker === "patient" ? "text-cyan-400" : "text-slate-400"
                          }`}>
                            {entry.speaker === "patient" ? "Patient (Bot)" : "Athena Agent"}
                          </span>
                          <p className="text-sm mt-1">{entry.text}</p>
                        </div>
                      ))
                    ) : (
                      <p className="text-slate-500 text-center py-8">No transcript available.</p>
                    )}
                  </div>
                  {/* Quick Bug Report */}
                  <div className="mt-4 pt-4 border-t border-slate-800">
                    <button
                      data-testid="report-bug-from-transcript"
                      onClick={() => {
                        setBugForm({ ...bugForm, call_id: selectedCall.id });
                        setActiveTab("bugs");
                      }}
                      className="text-sm text-red-400 hover:text-red-300 flex items-center gap-2"
                    >
                      <Bug className="w-4 h-4" />
                      Report bug from this call
                    </button>
                  </div>
                </div>
              ) : (
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center">
                  <FileText className="w-12 h-12 text-slate-700 mx-auto mb-3" />
                  <p className="text-slate-500">Select a call to view its transcript</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Bugs Tab */}
        {activeTab === "bugs" && (
          <div className="grid lg:grid-cols-2 gap-6">
            {/* Bug Report Form */}
            <div>
              <h2 className="text-lg font-semibold mb-4">Report a Bug</h2>
              <form onSubmit={submitBugReport} className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4">
                <div>
                  <label className="block text-sm text-slate-400 mb-2">Related Call</label>
                  <select
                    data-testid="bug-call-select"
                    value={bugForm.call_id}
                    onChange={(e) => setBugForm({ ...bugForm, call_id: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500"
                    required
                  >
                    <option value="">Select a call...</option>
                    <option value="manual-testing">Manual Testing (No Call)</option>
                    {calls.map((call) => (
                      <option key={call.id} value={call.id}>
                        {call.scenario_name} - {new Date(call.started_at).toLocaleDateString()}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-slate-400 mb-2">Bug Title</label>
                  <input
                    data-testid="bug-description-input"
                    type="text"
                    value={bugForm.bug_description}
                    onChange={(e) => setBugForm({ ...bugForm, bug_description: e.target.value })}
                    placeholder="Brief description of the issue"
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500"
                    required
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-slate-400 mb-2">Severity</label>
                    <select
                      data-testid="bug-severity-select"
                      value={bugForm.severity}
                      onChange={(e) => setBugForm({ ...bugForm, severity: e.target.value })}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500"
                    >
                      <option value="critical">Critical</option>
                      <option value="high">High</option>
                      <option value="medium">Medium</option>
                      <option value="low">Low</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm text-slate-400 mb-2">Timestamp in Call</label>
                    <input
                      data-testid="bug-timestamp-input"
                      type="text"
                      value={bugForm.timestamp_in_call}
                      onChange={(e) => setBugForm({ ...bugForm, timestamp_in_call: e.target.value })}
                      placeholder="e.g., 1:23"
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm text-slate-400 mb-2">Details</label>
                  <textarea
                    data-testid="bug-details-input"
                    value={bugForm.details}
                    onChange={(e) => setBugForm({ ...bugForm, details: e.target.value })}
                    placeholder="Detailed explanation of what happened and why it's a problem..."
                    rows={4}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500 resize-none"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm text-slate-400 mb-2">Recommendation (Optional)</label>
                  <textarea
                    data-testid="bug-recommendation-input"
                    value={bugForm.recommendation}
                    onChange={(e) => setBugForm({ ...bugForm, recommendation: e.target.value })}
                    placeholder="Suggested fix or improvement..."
                    rows={2}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500 resize-none"
                  />
                </div>
                <button
                  data-testid="submit-bug-btn"
                  type="submit"
                  className="w-full bg-red-600 hover:bg-red-500 text-white font-medium px-4 py-2 rounded-lg transition-colors flex items-center justify-center gap-2"
                >
                  <Bug className="w-4 h-4" />
                  Submit Bug Report
                </button>
              </form>
            </div>

            {/* Bug List */}
            <div>
              <h2 className="text-lg font-semibold mb-4">
                Bug Reports ({bugs.length})
                {bugs.filter(b => b.auto_detected).length > 0 && (
                  <span className="text-sm font-normal text-slate-500 ml-2">
                    ({bugs.filter(b => b.auto_detected).length} auto-detected)
                  </span>
                )}
              </h2>
              <div className="space-y-3 max-h-[calc(100vh-250px)] overflow-y-auto">
                {bugs.length === 0 ? (
                  <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center">
                    <Bug className="w-12 h-12 text-slate-700 mx-auto mb-3" />
                    <p className="text-slate-500">No bugs reported yet.</p>
                  </div>
                ) : (
                  bugs.map((bug) => (
                    <div
                      key={bug.id}
                      data-testid={`bug-item-${bug.id}`}
                      className="bg-slate-900 border border-slate-800 rounded-xl p-4"
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className={`px-2 py-1 rounded text-xs font-medium border ${getSeverityColor(bug.severity)}`}>
                            {bug.severity.toUpperCase()}
                          </span>
                          {bug.auto_detected && (
                            <span className="px-2 py-1 rounded text-xs font-medium bg-purple-950 text-purple-400 flex items-center gap-1">
                              <Zap className="w-3 h-3" />
                              Auto
                            </span>
                          )}
                        </div>
                        <button
                          data-testid={`delete-bug-${bug.id}`}
                          onClick={() => deleteBug(bug.id)}
                          className="text-slate-500 hover:text-red-400 transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                      <h3 className="font-medium mb-2">{bug.bug_description}</h3>
                      <p className="text-sm text-slate-400 mb-2 whitespace-pre-wrap">{bug.details}</p>
                      {bug.recommendation && (
                        <div className="mt-2 p-2 bg-slate-800/50 rounded text-xs text-slate-300">
                          <span className="text-emerald-400 font-medium">Recommendation:</span> {bug.recommendation}
                        </div>
                      )}
                      <div className="flex items-center gap-4 text-xs text-slate-500 mt-3">
                        {bug.timestamp_in_call && <span>@ {bug.timestamp_in_call}</span>}
                        <span>{new Date(bug.created_at).toLocaleDateString()}</span>
                        <span className="text-slate-600">Call: {bug.call_id?.substring(0, 8)}...</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800 bg-slate-900/30 mt-auto">
        <div className="max-w-7xl mx-auto px-6 py-4 text-center text-xs text-slate-500">
          Pretty Good AI Engineering Challenge - Athena Voice Bot Tester | Target: +1-805-439-8008
        </div>
      </footer>
    </div>
  );
}

export default App;
