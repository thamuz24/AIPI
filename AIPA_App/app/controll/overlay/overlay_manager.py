import json
import os
import subprocess
import sys
import time
import ctypes
from pathlib import Path
from typing import Any, Dict, List, Optional


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


class DesktopGridOverlayManager:
    def __init__(self, base_dir: Path, rows: int = 6, cols: int = 6) -> None:
        self.base_dir = Path(base_dir).resolve()
        self.overlay_dir = self.base_dir / 'overlay'
        self.tmp_dir = self.base_dir / 'tmp'
        self.script_file = self.overlay_dir / 'grid_overlay.py'
        self.command_file = self.tmp_dir / 'grid_overlay_command.json'
        self.status_file = self.tmp_dir / 'grid_overlay_status.json'
        self.pid_file = self.tmp_dir / 'grid_overlay.pid'
        self.default_rows = max(1, int(rows))
        self.default_cols = max(1, int(cols))

    def available(self) -> bool:
        return self.script_file.exists()

    def _raw_status(self) -> Dict[str, Any]:
        return _read_json(self.status_file)

    def _read_pid_file(self) -> int:
        try:
            return int(self.pid_file.read_text(encoding='utf-8').strip() or '0')
        except Exception:
            return 0

    def _candidate_pids(self) -> List[int]:
        values = {
            int(self._raw_status().get('pid') or 0),
            int(self._read_pid_file() or 0),
        }
        for pid in self._find_overlay_pids():
            values.add(int(pid))
        return [pid for pid in values if pid > 0]

    def _find_overlay_pids(self) -> List[int]:
        if os.name != 'nt':
            return []
        try:
            script_text = str(self.script_file).replace("'", "''")
            command = (
                "$script = '" + script_text + "'; "
                "Get-CimInstance Win32_Process | "
                "Where-Object { $_.CommandLine -like \"*grid_overlay.py*\" -or $_.CommandLine -like \"*$script*\" } | "
                "Select-Object -ExpandProperty ProcessId"
            )
            completed = subprocess.run(
                ['powershell', '-NoProfile', '-Command', command],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=8,
                check=False,
            )
            pids = []
            for line in str(completed.stdout or '').splitlines():
                line = line.strip()
                if line.isdigit():
                    pids.append(int(line))
            return pids
        except Exception:
            return []

    def _is_pid_alive(self, pid: int) -> bool:
        if not pid or pid <= 0:
            return False
        if os.name == 'nt':
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
            if not handle:
                return False
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        try:
            os.kill(int(pid), 0)
        except OSError:
            return False
        except Exception:
            return False
        return True

    def _terminate_pid(self, pid: int) -> bool:
        if not self._is_pid_alive(pid):
            return False
        try:
            if os.name == 'nt':
                subprocess.run(
                    ['taskkill', '/PID', str(int(pid)), '/T', '/F'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                    timeout=10,
                )
            else:
                os.kill(int(pid), 9)
        except Exception:
            return False
        return not self._is_pid_alive(pid)

    def _terminate_known_overlay(self) -> None:
        for pid in self._candidate_pids():
            self._terminate_pid(pid)

    def _clear_state(self, *, last_action: str = 'hide', last_error: str = '') -> Dict[str, Any]:
        payload = {
            'running': False,
            'visible': False,
            'zoom_cell': '',
            'rows': self.default_rows,
            'cols': self.default_cols,
            'pid': 0,
            'last_request_id': str(time.time()),
            'last_action': last_action,
            'last_error': last_error,
            'updated_at': time.time(),
            'screen_width': 0,
            'screen_height': 0,
        }
        _write_json(self.status_file, payload)
        try:
            if self.pid_file.exists():
                self.pid_file.unlink()
        except Exception:
            pass
        return self.get_status()

    def get_status(self) -> Dict[str, Any]:
        status = self._raw_status()
        now = time.time()
        updated_at = float(status.get('updated_at') or 0.0)
        heartbeat_age = max(0.0, now - updated_at) if updated_at else 9999.0
        pid = int(status.get('pid') or 0)
        if not pid:
            pid = self._read_pid_file()
        pid_alive = self._is_pid_alive(pid)
        is_running = bool(status.get('running')) and pid_alive and heartbeat_age <= 4.0
        visible = bool(status.get('visible')) if pid_alive else False
        return {
            'available': self.available(),
            'running': is_running,
            'visible': visible,
            'zoom_cell': str(status.get('zoom_cell') or ''),
            'rows': int(status.get('rows') or self.default_rows),
            'cols': int(status.get('cols') or self.default_cols),
            'pid': pid,
            'last_request_id': str(status.get('last_request_id') or ''),
            'last_action': str(status.get('last_action') or ''),
            'last_error': str(status.get('last_error') or ''),
            'screen_width': int(status.get('screen_width') or 0),
            'screen_height': int(status.get('screen_height') or 0),
            'updated_at': updated_at,
        }

    def ensure_running(self, timeout: float = 12.0) -> Dict[str, Any]:
        current = self.get_status()
        if current.get('pid') and self._is_pid_alive(int(current.get('pid') or 0)):
            return current
        if not self.available():
            raise RuntimeError(f'Khong tim thay overlay script: {self.script_file.as_posix()}')

        self._terminate_known_overlay()
        self._clear_state(last_action='reset')
        self.tmp_dir.mkdir(parents=True, exist_ok=True)

        creationflags = 0
        startupinfo = None
        if os.name == 'nt':
            creationflags = (
                getattr(subprocess, 'DETACHED_PROCESS', 0)
                | getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)
                | getattr(subprocess, 'CREATE_NO_WINDOW', 0)
            )
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        args = [
            sys.executable,
            str(self.script_file),
            '--command-file',
            str(self.command_file),
            '--status-file',
            str(self.status_file),
            '--pid-file',
            str(self.pid_file),
            '--rows',
            str(self.default_rows),
            '--cols',
            str(self.default_cols),
        ]
        subprocess.Popen(
            args,
            cwd=str(self.base_dir),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
            startupinfo=startupinfo,
        )

        deadline = time.time() + max(2.0, timeout)
        while time.time() < deadline:
            status = self.get_status()
            if status.get('pid') and self._is_pid_alive(int(status.get('pid') or 0)):
                return status
            time.sleep(0.2)
        raise RuntimeError('Overlay toa do khong khoi dong kip.')

    def _send_command(
        self,
        action: str,
        *,
        rows: Optional[int] = None,
        cols: Optional[int] = None,
        focus: str = '',
        timeout: float = 4.0,
    ) -> Dict[str, Any]:
        if action in {'show', 'zoom', 'reset'}:
            self.ensure_running()
        elif action in {'hide', 'stop'}:
            status = self.get_status()
            if not status.get('pid') or not self._is_pid_alive(int(status.get('pid') or 0)):
                return self._clear_state(last_action=action)

        request_id = f'{time.time():.6f}'
        payload = {
            'request_id': request_id,
            'action': action,
            'rows': int(rows or self.default_rows),
            'cols': int(cols or self.default_cols),
            'focus': str(focus or '').strip().lower(),
            'sent_at': time.time(),
        }
        _write_json(self.command_file, payload)

        deadline = time.time() + max(0.8, timeout)
        last_status = self.get_status()
        while time.time() < deadline:
            status = self.get_status()
            last_status = status
            if status.get('last_request_id') == request_id:
                if action == 'show' and status.get('visible'):
                    return status
                if action == 'hide' and not status.get('visible'):
                    return status
                if action == 'stop' and not status.get('pid'):
                    return status
            if action == 'hide' and not status.get('visible'):
                return status
            if action == 'stop' and not status.get('pid'):
                return status
            time.sleep(0.15)

        if action in {'hide', 'stop'}:
            pid = int(last_status.get('pid') or 0)
            if pid:
                self._terminate_pid(pid)
            return self._clear_state(last_action=action)
        return last_status

    def show(self, *, rows: Optional[int] = None, cols: Optional[int] = None, focus: str = '') -> Dict[str, Any]:
        self.stop()
        return self._send_command('show', rows=rows, cols=cols, focus=focus, timeout=5.0)

    def hide(self) -> Dict[str, Any]:
        return self.stop()

    def stop(self) -> Dict[str, Any]:
        self._terminate_known_overlay()
        return self._clear_state(last_action='stop')
