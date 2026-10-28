# Paper summaries and progress

Paper analysis uses the versioned [brief template](../prompts/paper-brief.md),
with `gpt-6.1-sol` and `medium` reasoning by default. The model request has a
150-second limit. The usual output is 400–700 Chinese characters: one sentence,
motivation, the core method/differentiator, and the strongest evidence/limitations.
Missing or partial evidence is disclosed. Research proposals and reproduction
plans are no longer part of this quick summary. General document assistance keeps
its separate model/reasoning/timeout configuration.

Lower reasoning effort favors speed and fewer tokens; see the
[OpenAI reasoning guide](https://platform.openai.com/docs/guides/reasoning).
The configured model name is kept unchanged; deployment checks must use the
running service's actual model-provider configuration.

## PDF upload and extraction

The browser sends file bytes directly to the authenticated upload endpoint,
which writes a bounded stream to a temporary file before committing its metadata.
This avoids multipart temporary-file copying. The upload bar uses XHR's actual
transmitted bytes; remaining time uses a recent throughput window. Before enough
transfer data arrives, or while the connection stalls, the UI does not invent a
transfer speed. Sending all bytes is separate from the server's confirmation.

A supplied PDF is parsed locally in parallel with upload. It is not downloaded
back from the server for extraction. Only this selected File object supplies the
analysis text; a link remains attribution and does not replace it. The normal
server-backed preview still lets the owner check the uploaded original.

Extraction reports completed pages against its bounded page target. Remaining
time uses recent completed pages, avoiding first-page initialization overhead;
unmeasurable/stalled work is labelled accordingly. Existing limits remain 80
pages, 60,000 characters and 45 seconds. Reaching a text/page limit is clearly
marked as partial extraction. URL downloads show a separate stage because the
upstream content length/throughput is not always observable.

## AI jobs and estimates

`POST /api/papers/draft` with `background: true` starts an authenticated transient
job. `GET /api/papers/jobs/<id>` reports its actual state and result. The original
synchronous endpoint remains compatible, and `generate: false` still archives a
PDF without invoking AI. Jobs never create a document; insertion and save remain
explicit. Concurrent duplicate requests reuse the active job, and a different
paper is rejected while a paper job is running. Normal assistant execution also
retains its process-level concurrency guard and process-group timeout cleanup.

The model does not provide a trustworthy percentage of reasoning completed. The
UI therefore labels AI progress as **预估进度**, using elapsed wall time and
recent successful task durations, grouped by input length. The estimated range
widens when samples are sparse. Only a completed result reaches 100%; an overrun
switches to an indeterminate bar and an explicit elapsed-time message rather than
sticking at a fake 99% or counting below zero.

Only elapsed seconds and character counts are persisted in the private
`WORKSPACE_DATA_DIR/paper-timings.json`, together with a hash of the model,
reasoning setting and prompt. No paper title, text, response or file identifier
is stored in these samples. Changing the prompt or reasoning profile resets
calibration. This optional cache is not part of document exports or required
backups; restoring without it starts a new estimate history. Browser-local
acknowledgement timing contains only numeric durations.

Job results stay in bounded process memory for at most fifteen minutes and are
available only to the signed-in owner. A service restart loses pending jobs;
the UI offers retry. Measurements are estimates, not guarantees against network
or provider load changes. Calibrate a deployment using public/synthetic material,
then let real completed tasks improve the estimates without logging content.
