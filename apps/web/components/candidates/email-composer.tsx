"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { api, ApiError } from "@/lib/api";
import type { ApplicationDetail } from "@/types/api";

interface EmailComposerProps {
  application: ApplicationDetail;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function htmlToPlain(html: string): string {
  if (typeof document === "undefined") return html;
  const el = document.createElement("div");
  el.innerHTML = html;
  return el.textContent ?? el.innerText ?? html;
}

export function EmailComposer({ application, open, onOpenChange }: EmailComposerProps) {
  const queryClient = useQueryClient();
  const templates = useQuery({
    queryKey: ["email-templates"],
    queryFn: () => api.emails.listTemplates(),
    enabled: open,
  });

  const [templateKey, setTemplateKey] = useState("");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [to, setTo] = useState(application.candidate.email);

  useEffect(() => {
    if (open) {
      setTo(application.candidate.email);
      setTemplateKey("");
      setSubject("");
      setBody("");
    }
  }, [open, application.candidate.email]);

  const preview = useMutation({
    mutationFn: () =>
      api.emails.preview({
        subject,
        body_html: body.replace(/\n/g, "<br />"),
        variables: {
          candidate_name: `${application.candidate.first_name} ${application.candidate.last_name}`,
          job_title: application.job.name,
        },
      }),
    onSuccess: (result) => {
      setSubject(result.subject);
      setBody(htmlToPlain(result.body_html));
    },
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : "Could not preview email"),
  });

  const send = useMutation({
    mutationFn: () =>
      api.emails.send({
        candidate_id: application.candidate.id,
        application_id: application.id,
        template_key: templateKey || null,
        to: to.trim() || null,
        subject: subject.trim(),
        body,
      }),
    onSuccess: () => {
      toast.success("Email queued");
      onOpenChange(false);
      void queryClient.invalidateQueries({
        queryKey: ["candidates", "emails", application.candidate.id],
      });
    },
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : "Could not send email"),
  });

  const applyTemplate = (key: string) => {
    setTemplateKey(key);
    const tpl = templates.data?.find((t) => t.key === key);
    if (!tpl) return;
    setSubject(tpl.subject);
    setBody(htmlToPlain(tpl.body_html));
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Email candidate</DialogTitle>
          <DialogDescription>
            Messages are sent from your organization. Preview substitutes candidate and job
            variables.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email-template">Template</Label>
            <Select
              id="email-template"
              value={templateKey}
              onChange={(e) => applyTemplate(e.target.value)}
              disabled={templates.isPending}
            >
              <option value="">Custom message</option>
              {(templates.data ?? [])
                .filter((t) => t.is_active)
                .map((t) => (
                  <option key={t.id} value={t.key}>
                    {t.key}
                  </option>
                ))}
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="email-to">To</Label>
            <Input id="email-to" value={to} onChange={(e) => setTo(e.target.value)} type="email" />
          </div>
          <div className="space-y-2">
            <Label htmlFor="email-subject">Subject</Label>
            <Input
              id="email-subject"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="email-body">Body</Label>
            <Textarea
              id="email-body"
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={8}
            />
          </div>
        </div>
        <DialogFooter className="gap-2 sm:justify-between">
          <Button
            type="button"
            variant="outline"
            disabled={!subject.trim() || !body.trim() || preview.isPending}
            onClick={() => preview.mutate()}
          >
            {preview.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden />}
            Preview variables
          </Button>
          <div className="flex gap-2">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button
              type="button"
              disabled={!subject.trim() || !body.trim() || send.isPending}
              onClick={() => send.mutate()}
            >
              {send.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden />}
              Send
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
