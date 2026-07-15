"""Test de humo de la GUI: instancia EcoClockWindow en offscreen y simula login/submit con monkeypatch sobre services.

Requiere PyQt6 instalado. Si no lo esta, el modulo entero se salta.
"""

from __future__ import annotations

import os

# Si no hay display real y no estamos en offscreen, marcamos skip.
# pytest-qt suele aportar esto, pero como no lo usamos, lo hacemos a mano.
if not os.environ.get("QT_QPA_PLATFORM"):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PyQt6", reason="PyQt6 no instalado")

from PyQt6.QtWidgets import QApplication  # noqa: E402

from client.gui import app as gui_app  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app
    # No llamamos app.quit() para no romper otros tests del modulo.


@pytest.fixture
def window(qapp):
    return gui_app.EcoClockWindow()


def test_window_has_two_pages(window):
    assert window.stack.count() == 2
    assert window.stack.currentIndex() == window.PAGE_LOGIN


def test_login_page_has_inputs_and_button(window):
    assert window.username_input.placeholderText() == "username"
    assert window.password_input.echoMode() == window.password_input.EchoMode.Password
    assert window.login_button.text() == "Entrar"


def test_task_page_has_label_output_and_button(window):
    assert window.task_label.text() == "(sin tarea)"
    assert "ndvi" in window.task_output.placeholderText()
    assert window.submit_button.text() == "Enviar"


def test_login_success_jumps_to_task_page(window, monkeypatch):
    calls = {"login": 0, "next": 0, "submit": 0}

    def fake_login(base_url, email, password):
        calls["login"] += 1
        assert email == "u@example.com"
        return {"access_token": "tok-123"}

    def fake_next(base_url, token):
        calls["next"] += 1
        assert token == "tok-123"
        return {"id": 7, "name": "ndvi-dummy"}

    monkeypatch.setattr("client.gui.services.login", fake_login)
    monkeypatch.setattr("client.gui.services.next_task", fake_next)

    window.username_input.setText("u@example.com")
    window.password_input.setText("secret")
    window._on_login_clicked()

    assert calls["login"] == 1
    assert calls["next"] == 1
    assert window._token == "tok-123"
    assert window._current_task == {"id": 7, "name": "ndvi-dummy"}
    assert window.stack.currentIndex() == window.PAGE_TASK
    assert "Tarea #7" in window.task_label.text()
    assert "ndvi-dummy" in window.task_label.text()


def test_login_with_empty_fields_shows_warning(window, monkeypatch):
    called = {"login": 0}

    def fake_login(*a, **kw):
        called["login"] += 1
        return {}

    monkeypatch.setattr("client.gui.services.login", fake_login)
    # QMessageBox.warning es modal: monkeypatch para que no bloquee.
    monkeypatch.setattr(
        "client.gui.app.QMessageBox.warning",
        lambda *a, **kw: print("warning:", a[2]),
    )
    window._on_login_clicked()
    assert called["login"] == 0
    assert window.stack.currentIndex() == window.PAGE_LOGIN


def test_submit_calls_services_and_fetches_next(window, monkeypatch):
    # Sembramos un login + tarea previos.
    window._token = "tok-123"
    window._current_task = {"id": 7, "name": "ndvi-dummy"}
    window.stack.setCurrentIndex(window.PAGE_TASK)

    calls = {"submit": 0, "next": 0}

    def fake_submit(base_url, token, task_id, output, compute_time_sec):
        calls["submit"] += 1
        assert task_id == 7
        assert output == {"ndvi": 0.5}
        return {"status": "ok"}

    def fake_next(base_url, token):
        calls["next"] += 1
        return {"id": 8, "name": "otra"}

    monkeypatch.setattr("client.gui.services.submit_task", fake_submit)
    monkeypatch.setattr("client.gui.services.next_task", fake_next)

    window.task_output.setPlainText('{"ndvi": 0.5}')
    window._on_submit_clicked()

    assert calls["submit"] == 1
    assert calls["next"] == 1
    assert window._current_task == {"id": 8, "name": "otra"}


def test_submit_with_invalid_json_does_not_call_service(window, monkeypatch):
    window._token = "tok-123"
    window._current_task = {"id": 7, "name": "ndvi-dummy"}
    window.stack.setCurrentIndex(window.PAGE_TASK)

    called = {"submit": 0}

    def fake_submit(*a, **kw):
        called["submit"] += 1
        return {}

    monkeypatch.setattr("client.gui.services.submit_task", fake_submit)
    monkeypatch.setattr(
        "client.gui.app.QMessageBox.warning",
        lambda *a, **kw: print("warning:", a[2]),
    )
    window.task_output.setPlainText("not json")
    window._on_submit_clicked()
    assert called["submit"] == 0


def test_logout_returns_to_login(window):
    window._token = "tok-123"
    window._current_task = {"id": 7, "name": "x"}
    window.username_input.setText("u@example.com")
    window.password_input.setText("secret")
    window.stack.setCurrentIndex(window.PAGE_TASK)

    window._logout()

    assert window._token is None
    assert window._current_task is None
    assert window.username_input.text() == ""
    assert window.password_input.text() == ""
    assert window.stack.currentIndex() == window.PAGE_LOGIN
