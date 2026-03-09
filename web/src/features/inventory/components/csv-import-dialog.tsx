import { useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { inventoryApi } from "@/features/inventory/api";
import { queryKeys } from "@/lib/query-keys";
import { ApiClientError } from "@/lib/api-client";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Upload, FileSpreadsheet, CheckCircle, AlertCircle } from "lucide-react";

type CsvImportDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

export function CsvImportDialog({ open, onOpenChange }: CsvImportDialogProps) {
  const queryClient = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<{ status: string; processed: number; errors: string[] } | null>(null);

  const mutation = useMutation({
    mutationFn: (f: File) => inventoryApi.importCsv(f),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.items.all });
      setResult({ status: "completed", processed: 0, errors: [] });
      toast.success("CSV import started");
    },
    onError: (err) => {
      if (err instanceof ApiClientError) {
        toast.error(err.errors[0]?.message ?? "Import failed");
      } else {
        toast.error("Import failed");
      }
    },
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) {
      if (!f.name.endsWith(".csv")) {
        toast.error("Please select a CSV file");
        return;
      }
      setFile(f);
      setResult(null);
    }
  };

  const handleImport = () => {
    if (file) mutation.mutate(file);
  };

  const handleClose = () => {
    setFile(null);
    setResult(null);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Import Items from CSV</DialogTitle>
          <DialogDescription>
            Upload a CSV file with columns: name, sku, cogs, sale_price, quantity, status, notes
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {!result ? (
            <>
              <div
                className="flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-colors hover:border-primary/50 hover:bg-muted/50"
                onClick={() => fileRef.current?.click()}
              >
                {file ? (
                  <>
                    <FileSpreadsheet className="h-10 w-10 text-primary" />
                    <p className="mt-2 text-sm font-medium">{file.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {(file.size / 1024).toFixed(1)} KB
                    </p>
                  </>
                ) : (
                  <>
                    <Upload className="h-10 w-10 text-muted-foreground" />
                    <p className="mt-2 text-sm font-medium">Click to select a CSV file</p>
                    <p className="text-xs text-muted-foreground">or drag and drop</p>
                  </>
                )}
              </div>
              <input
                ref={fileRef}
                type="file"
                accept=".csv"
                className="hidden"
                onChange={handleFileChange}
              />
            </>
          ) : (
            <div className="flex flex-col items-center gap-3 py-4">
              {result.errors.length === 0 ? (
                <>
                  <CheckCircle className="h-10 w-10 text-green-500" />
                  <p className="text-sm font-medium">Import started successfully</p>
                  <p className="text-xs text-muted-foreground">
                    Your items will appear shortly.
                  </p>
                </>
              ) : (
                <>
                  <AlertCircle className="h-10 w-10 text-destructive" />
                  <p className="text-sm font-medium">Import completed with errors</p>
                  <ul className="max-h-32 w-full overflow-y-auto rounded border p-2 text-xs text-destructive">
                    {result.errors.map((err, i) => (
                      <li key={i}>{err}</li>
                    ))}
                  </ul>
                </>
              )}
            </div>
          )}
        </div>

        <DialogFooter>
          {result ? (
            <Button onClick={handleClose}>Done</Button>
          ) : (
            <>
              <Button variant="outline" onClick={handleClose}>
                Cancel
              </Button>
              <Button onClick={handleImport} disabled={!file || mutation.isPending}>
                {mutation.isPending ? "Importing…" : "Import"}
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
