import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router";
import { authApi } from "@/features/auth/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { CheckCircle, XCircle, Loader2 } from "lucide-react";

export function VerifyEmailPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setErrorMessage("Invalid verification link. No token provided.");
      return;
    }

    authApi
      .verifyEmail(token)
      .then(() => setStatus("success"))
      .catch((err) => {
        setStatus("error");
        setErrorMessage(err instanceof Error ? err.message : "Verification failed.");
      });
  }, [token]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-primary">
            <span className="text-xl font-bold text-primary-foreground">W</span>
          </div>
        </div>

        <Card>
          {status === "loading" && (
            <CardHeader className="text-center">
              <div className="mx-auto mb-4">
                <Loader2 className="h-10 w-10 animate-spin text-primary" />
              </div>
              <CardTitle>Verifying your email</CardTitle>
              <CardDescription>Please wait while we verify your email address…</CardDescription>
            </CardHeader>
          )}

          {status === "success" && (
            <>
              <CardHeader className="text-center">
                <div className="mx-auto mb-4">
                  <CheckCircle className="h-10 w-10 text-green-500" />
                </div>
                <CardTitle>Email verified!</CardTitle>
                <CardDescription>
                  Your email has been verified. You can now sign in to your account.
                </CardDescription>
              </CardHeader>
              <CardFooter>
                <Button asChild className="w-full">
                  <Link to="/login">Sign In</Link>
                </Button>
              </CardFooter>
            </>
          )}

          {status === "error" && (
            <>
              <CardHeader className="text-center">
                <div className="mx-auto mb-4">
                  <XCircle className="h-10 w-10 text-destructive" />
                </div>
                <CardTitle>Verification failed</CardTitle>
                <CardDescription>{errorMessage}</CardDescription>
              </CardHeader>
              <CardFooter>
                <Button asChild className="w-full" variant="outline">
                  <Link to="/login">Go to Sign In</Link>
                </Button>
              </CardFooter>
            </>
          )}
        </Card>
      </div>
    </div>
  );
}
