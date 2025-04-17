"use client";

import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Loader2, ActivitySquare } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { useToast } from "@/hooks/use-toast";
import { isLocalhost } from "@/lib/utils";
import { AuthModal } from "@/components/ui/AuthModal";
import { useSettings } from "../contexts/SettingsContext";
import { useSteelContext } from "../contexts/SteelContext";

interface Result {
  test_id?: string;
  report_id?: string;
  report?: any;
  rawReport?: string;
  status?: string;
}

export default function BatchRequestPage() {
  const { currentSettings, updateSettings } = useSettings();
  const { resetSession } = useSteelContext();
  const { toast } = useToast();
  
  const [loading, setLoading] = useState(false);
  const [url, setUrl] = useState("");
  const [description, setDescription] = useState("");
  const [modelChoice, setModelChoice] = useState("gpt-4o");
  const [temperature, setTemperature] = useState(0.7);
  const [timeout, setTimeout] = useState(300);
  const [result, setResult] = useState<Result | null>(null);
  const [activeTab, setActiveTab] = useState<"form" | "result">("form");
  const [error, setError] = useState("");
  const [polling, setPolling] = useState<boolean>(false);
  const [showApiKeyModal, setShowApiKeyModal] = useState(false);
  
  // Store the pending request when waiting for API key
  const pendingRequestRef = useRef<any>(null);

  // Reset session on mount
  useEffect(() => {
    resetSession();
  }, []);

  const checkApiKey = () => {
    // For demo purposes, always return true
    // In a real implementation, use the same logic as in test/page.tsx
    return true;
  };

  const handleApiKeySubmit = (key: string) => {
    const provider = currentSettings?.selectedProvider;
    if (!provider) return;
    
    // Update settings with new API key
    const currentKeys = currentSettings?.providerApiKeys || {};
    updateSettings({
      ...currentSettings!,
      providerApiKeys: {
        ...currentKeys,
        [provider]: key,
      },
    });
    
    setShowApiKeyModal(false);
    
    // Process the pending request
    if (pendingRequestRef.current) {
      handleBatchRequest(pendingRequestRef.current);
      pendingRequestRef.current = null;
    }
  };

  const checkStatus = async (test_id: string) => {
    try {
      const response = await fetch(`/api/batch/status/${test_id}`);
      const data = await response.json();

      if (response.ok) {
        // If we have a report, update the result
        if (data.report) {
          setResult({
            ...result,
            report: data.report,  // Store the entire report object
            rawReport: typeof data.report === 'string' ? data.report : JSON.stringify(data.report, null, 2),
            status: data.status
          });
        } else {
          // No report yet, just update status
          setResult({
            ...result,
            status: data.status
          });
        }

        // If status is complete or failed, stop polling
        if (data.status === "complete" || data.status === "failed") {
          setPolling(false);
        }
      } else {
        // Error
        setError(data.message || "Failed to check status");
        setPolling(false);
      }
    } catch (e) {
      setError("Error checking test status: " + (e as Error).message);
      setPolling(false);
    }
  };

  const handleBatchRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    
    try {
      const response = await fetch("/api/batch/browser_agent", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          url,
          description,
          provider: "azure_openai",
          model_settings: {
            model_choice: modelChoice,
            temperature,
          },
          timeout,
        }),
      });

      const data = await response.json();
      
      // Process the response
      if (data.test_id) {
        // Create a raw report string for display purposes
        const rawReport = data.report ? 
          (typeof data.report === 'string' ? data.report : JSON.stringify(data.report, null, 2)) : 
          null;
        
        setResult({
          test_id: data.test_id,
          report_id: data.report_id || 'N/A',
          status: data.status || 'pending',
          report: data.report, // Store the original report data without assumptions
          rawReport: rawReport
        });
        
        // Start polling for status updates if not completed
        if (data.status !== "completed" && data.status !== "failed") {
          checkStatus(data.test_id);
        }
        
        setActiveTab("result");
      } else if (data.status === "error") {
        // Handle API error response
        setError(data.message || "Unknown error occurred");
      } else {
        setError("Invalid response from server.");
      }
    } catch (error) {
      console.error("Error in batch request:", error);
      setError("Failed to send request: " + (error instanceof Error ? error.message : String(error)));
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim() || loading) return;
    
    setError("");
    setResult(null);
    
    const requestData = {
      url,
      description,
      provider: "azure_openai",
      model_settings: {
        model_choice: modelChoice,
        temperature,
      },
      timeout,
    };

    try {
      // Reset the session before making a new request
      resetSession();
      
      // Check if we have the API key
      if (!checkApiKey()) {
        if (currentSettings?.selectedProvider === "ollama" && !isLocalhost()) {
          toast({
            title: "Cannot use Ollama",
            className: "text-[var(--gray-12)] border border-[var(--red-11)] bg-[var(--red-2)] text-sm",
            description: "Please select a different model provider or run the app locally to use Ollama.",
          });
        } else {
          pendingRequestRef.current = requestData;
          setShowApiKeyModal(true);
        }
        return;
      }
      
      await handleBatchRequest(e);
      
    } catch (err) {
      console.error("Error in batch request:", err);
      setError("Failed to process request: " + (err instanceof Error ? err.message : String(err)));
    }
  };

  // Reset state when changing tab to form
  const handleFormTabClick = () => {
    if (activeTab !== "form") {
      setActiveTab("form");
      if (polling) {
        // Stop polling if active
        setPolling(false);
      }
    }
  };
  
  // Switch to results tab
  const handleResultsTabClick = () => {
    if (result && activeTab !== "result") {
      setActiveTab("result");
    }
  };
  
  // Auto-switch to results tab when we get results
  useEffect(() => {
    if (result && !polling) {
      setActiveTab("result");
    }
  }, [result, polling]);

  // Render the results section
  const renderResults = () => {
    if (!result) return null;

    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h2 className="text-xl font-semibold">Test Results</h2>
          <Button variant="outline" onClick={() => setActiveTab("form")}>
            Return to Form
          </Button>
        </div>

        <div className="space-y-3">
          <div className="grid grid-cols-3 gap-4">
            <div>
              <h3 className="text-sm font-medium text-muted-foreground">Test ID</h3>
              <p className="break-all">{result.test_id}</p>
            </div>
            <div>
              <h3 className="text-sm font-medium text-muted-foreground">Report ID</h3>
              <p className="break-all">{result.report_id}</p>
            </div>
            <div>
              <h3 className="text-sm font-medium text-muted-foreground">Status</h3>
              <p className={`${result.status === "complete" ? "text-green-600" : result.status === "failed" ? "text-red-600" : "text-amber-600"}`}>
                {result.status}
              </p>
            </div>
          </div>
        </div>

        {/* Report content */}
        <div>
          <h3 className="text-lg font-medium mb-2">Report Content</h3>
          {result.report ? (
            <div className="space-y-4">
              {/* Try to display report content if it exists and has the right structure */}
              {typeof result.report === 'object' && (
                <pre className="bg-slate-50 dark:bg-slate-900 p-4 rounded-md overflow-auto max-h-[500px]">
                  {JSON.stringify(result.report, null, 2)}
                </pre>
              )}
              
              {/* Show plain text report if it's a string */}
              {typeof result.report === 'string' && (
                <pre className="bg-slate-50 dark:bg-slate-900 p-4 rounded-md overflow-auto max-h-[500px]">
                  {result.report}
                </pre>
              )}
            </div>
          ) : (
            <div className="space-y-4">
              <p className="text-muted-foreground">No report data available.</p>
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <main className="flex min-h-screen flex-col items-center justify-center">
      <div className="flex w-full flex-col gap-6 px-4 md:max-w-[800px]">
        <div className="p-4 text-justify font-geist text-base font-medium leading-tight text-[--gray-12]">
          Run browser agent tests in batch mode to analyze websites and generate comprehensive performance reports.
          Submit a URL and get a detailed analysis without the need for real-time streaming.
        </div>
        
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="mb-4 flex w-full rounded-lg bg-[--gray-3]">
            <TabsTrigger 
              value="form" 
              className="flex-1 rounded-md py-2 text-sm font-medium data-[state=active]:bg-white"
            >
              Request Form
            </TabsTrigger>
            <TabsTrigger 
              value="result" 
              className="flex-1 rounded-md py-2 text-sm font-medium data-[state=active]:bg-white"
            >
              Results
            </TabsTrigger>
          </TabsList>
          
          <TabsContent value="form">
            <Card className="border border-[--gray-3] bg-[--gray-1]">
              <CardHeader>
                <CardTitle className="text-[--gray-12]">Create a Batch Request</CardTitle>
                <CardDescription className="text-[--gray-11]">
                  Submit a URL to analyze using the browser agent in batch mode.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSubmit} className="space-y-6">
                  <div className="space-y-2">
                    <Label htmlFor="url" className="text-sm font-medium text-[--gray-12]">URL to Analyze</Label>
                    <Input
                      id="url"
                      placeholder="https://example.com"
                      value={url}
                      onChange={(e) => setUrl(e.target.value)}
                      required
                      className="border-[--gray-3] bg-white"
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <Label htmlFor="description" className="text-sm font-medium text-[--gray-12]">Description</Label>
                    <Textarea
                      id="description"
                      placeholder="Describe the purpose of this test"
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      className="border-[--gray-3] bg-white"
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <Label htmlFor="model" className="text-sm font-medium text-[--gray-12]">Model</Label>
                    <Select
                      value={modelChoice}
                      onValueChange={setModelChoice}
                    >
                      <SelectTrigger id="model" className="border-[--gray-3] bg-white">
                        <SelectValue placeholder="Select a model" />
                      </SelectTrigger>
                      <SelectContent className="bg-white">
                        <SelectItem value="gpt-4o">GPT-4o</SelectItem>
                        <SelectItem value="gpt-4o-mini">GPT-4o Mini</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <Label htmlFor="temperature" className="text-sm font-medium text-[--gray-12]">
                        Temperature: {temperature}
                      </Label>
                    </div>
                    <Slider
                      id="temperature"
                      min={0}
                      max={1}
                      step={0.05}
                      value={[temperature]}
                      onValueChange={(value) => setTemperature(value[0])}
                      className="py-2"
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <Label htmlFor="timeout" className="text-sm font-medium text-[--gray-12]">
                        Timeout (seconds): {timeout}
                      </Label>
                    </div>
                    <Slider
                      id="timeout"
                      min={60}
                      max={600}
                      step={30}
                      value={[timeout]}
                      onValueChange={(value) => setTimeout(value[0])}
                      className="py-2"
                    />
                  </div>
                  
                  {error && (
                    <Alert variant="destructive" className="mt-4 border border-[var(--red-11)] bg-[var(--red-2)]">
                      <AlertTitle className="text-[var(--red-11)]">Error</AlertTitle>
                      <AlertDescription className="text-[var(--red-11)]">{error}</AlertDescription>
                    </Alert>
                  )}
                  
                  <Button 
                    type="submit" 
                    className="mt-2 w-full bg-gradient-to-r from-blue-600 to-blue-700 text-white hover:from-blue-700 hover:to-blue-800" 
                    disabled={loading}
                  >
                    {loading ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Running Analysis...
                      </>
                    ) : (
                      "Run Batch Analysis"
                    )}
                  </Button>
                </form>
              </CardContent>
            </Card>
          </TabsContent>
          
          <TabsContent value="result">
            <Card className="border border-[--gray-3] bg-[--gray-1]">
              <CardHeader>
                <CardTitle className="text-[--gray-12]">Analysis Results</CardTitle>
                <CardDescription className="text-[--gray-11]">
                  Performance report for {url}
                </CardDescription>
                <Button variant="outline" onClick={() => setActiveTab("form")} className="mt-2 border-[--gray-5] text-[--gray-11] hover:text-[--gray-12]">
                  Back to Form
                </Button>
              </CardHeader>
              <CardContent>
                {renderResults()}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
      
      {/* API Key Modal */}
      <AuthModal
        provider={currentSettings?.selectedProvider || ""}
        isOpen={showApiKeyModal}
        onSubmit={handleApiKeySubmit}
      />
    </main>
  );
} 