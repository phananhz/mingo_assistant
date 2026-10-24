"""Close only the selected dossier's office documents, preserving unsaved edits."""
from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
from pathlib import Path
from collections.abc import Sequence


_CLOSE_DOCUMENTS_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$paths = ConvertFrom-Json ([Console]::In.ReadToEnd())
$targets = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
foreach ($path in $paths) { [void]$targets.Add([System.IO.Path]::GetFullPath($path)) }
Add-Type -TypeDefinition @'
using System;
using System.IO;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Runtime.InteropServices.ComTypes;
public static class DossierRunningDocuments {
    [DllImport("ole32.dll")] static extern int GetRunningObjectTable(int reserved, out IRunningObjectTable table);
    [DllImport("ole32.dll")] static extern int CreateBindCtx(int reserved, out IBindCtx context);
    public static object[] Find(string[] paths) {
        var wanted = new HashSet<string>(paths, StringComparer.OrdinalIgnoreCase);
        var found = new List<object>();
        IRunningObjectTable table = null;
        IBindCtx context = null;
        IEnumMoniker enumerator = null;
        try {
            Marshal.ThrowExceptionForHR(GetRunningObjectTable(0, out table));
            Marshal.ThrowExceptionForHR(CreateBindCtx(0, out context));
            table.EnumRunning(out enumerator);
            var slot = new IMoniker[1];
            while (enumerator.Next(1, slot, IntPtr.Zero) == 0) {
                try {
                    string name;
                    slot[0].GetDisplayName(context, null, out name);
                    name = name.TrimStart('!');
                    Uri uri;
                    if (Uri.TryCreate(name, UriKind.Absolute, out uri) && uri.IsFile) name = uri.LocalPath;
                    if (!wanted.Contains(Path.GetFullPath(name))) continue;
                    object document;
                    if (table.GetObject(slot[0], out document) == 0 && document != null) found.Add(document);
                } catch (Exception) {
                    // ROT entries can disappear while Word is closing files.
                } finally { Marshal.ReleaseComObject(slot[0]); }
            }
        } finally {
            if (enumerator != null) Marshal.ReleaseComObject(enumerator);
            if (context != null) Marshal.ReleaseComObject(context);
            if (table != null) Marshal.ReleaseComObject(table);
        }
        return found.ToArray();
    }
}
'@
$word = $null
try { $word = [Runtime.InteropServices.Marshal]::GetActiveObject('Word.Application') } catch {}
if ($null -ne $word) {
    for ($index = $word.Documents.Count; $index -ge 1; $index--) {
        $document = $word.Documents.Item($index)
        if (-not $targets.Contains([System.IO.Path]::GetFullPath($document.FullName))) { continue }
        if (-not $document.Saved) {
            if ($document.ReadOnly) { throw 'File chỉ đọc có thay đổi chưa lưu; chưa đóng để tránh mất dữ liệu.' }
            $document.Save()
        }
        $saveChanges = -1
        $document.Close([ref]$saveChanges)
    }
}
# A file moniker also finds documents in additional/hidden Word instances.
# It never binds to disk or opens a new document: only existing ROT entries
# matching an exact requested full path are returned.
foreach ($document in [DossierRunningDocuments]::Find([string[]]$paths)) {
    $fullName = [System.IO.Path]::GetFullPath($document.FullName)
    if (-not $targets.Contains($fullName)) { continue }
    if (-not $document.Saved) {
        if ($document.ReadOnly) { throw 'File chỉ đọc có thay đổi chưa lưu; chưa đóng để tránh mất dữ liệu.' }
        $document.Save()
    }
    $saveChanges = -1
    $document.Close([ref]$saveChanges)
}
"""


def close_open_documents(files: Sequence[Path]) -> None:
    if sys.platform != "win32":
        return
    executable = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    command = base64.b64encode(_CLOSE_DOCUMENTS_SCRIPT.encode("utf-16-le")).decode("ascii")
    try:
        result = subprocess.run(
            [str(executable), "-NoProfile", "-NonInteractive", "-EncodedCommand", command],
            input=json.dumps([str(path.resolve()) for path in files]), encoding="utf-8",
            capture_output=True, timeout=30, creationflags=0x08000000,  # CREATE_NO_WINDOW
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise OSError("Không thể hoàn tất đóng file đang mở. Hồ sơ chưa được chuyển; vui lòng kiểm tra Word.") from exc
    if result.returncode:
        raise OSError(
            "Không thể lưu hoặc đóng một file thuộc bộ hồ sơ. Hồ sơ chưa được chuyển. "
            "Vui lòng kiểm tra file chỉ đọc hoặc hộp thoại đang mở trong Word.\n"
            + result.stderr.strip()
        )
