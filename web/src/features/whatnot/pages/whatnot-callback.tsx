import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { Loader2, CheckCircle, XCircle } from "lucide-react";

import { api } from "@/lib/api-client";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export function WhatnotCallbackPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    const code = searchParams.get("code");
    const state = searchParams.get("state");
    const error = searchParams.get("error");

    if (error) {
      setStatus("error");
      setErrorMessage(error === "access_denied" ? "You denied access to your Whatnot account." : error);
      return;
    }

    if (!code || !state) {
      setStatus("error");
      setErrorMessage("Missing authorization code or state parameter.");
      return;
    }

    api
      .get(`/api/v1/whatnot/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`)
      .then(() => setStatus("success"))
      .catch((err) => {
        setStatus("error");
        setErrorMessage(err.message || "Failed to complete connection.");
      });
  }, [searchParams]);

  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle>
            {status === "loading" && "Connecting Whatnot..."}
            {status === "success" && "Connected!"}
            {status === "error" && "Connection Failed"}
          </CardTitle>
          <CardDescription>
            {status === "loading" && "Please wait while we complete your Whatnot connection."}
            {status === "success" && "Your Whatnot account has been connected successfully."}
            {status === "error" && errorMessage}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col items-center gap-4">
          {status === "loading" && <Loader2 className="h-10 w-10 animate-spin text-primary" />}
          {status === "success" && <CheckCircle className="h-10 w-10 text-green-500" />}
          {status === "error" && <XCircle className="h-10 w-10 text-destructive" />}

          {status !== "loading" && (
            <Button onClick={() => navigate("/settings/whatnot")} className="mt-2">
              Go to Whatnot Settings
            </Button>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
