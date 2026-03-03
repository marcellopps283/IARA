import pytest
from datetime import datetime, timedelta
import scheduler

def test_should_run_absolute_cron_first_time():
    now = datetime(2026, 1, 1, 10, 5) # 10:05 da manhã
    job = {
        "name": "daily",
        "cron": "10:00",
        "last_run": None
    }
    # Passou das 10:00 e last_run é nulo, logo DEVE rodar
    assert scheduler.should_run(job, now) is True

def test_should_run_absolute_cron_already_ran_today():
    now = datetime(2026, 1, 1, 10, 30)
    last = datetime(2026, 1, 1, 10, 5)
    job = {
        "name": "daily",
        "cron": "10:00",
        "last_run": last.isoformat()
    }
    # Já rodou hoje às 10:05, DEVE retornar False
    assert scheduler.should_run(job, now) is False

def test_should_run_interval_past_due():
    now = datetime(2026, 1, 1, 10, 10)
    last = now - timedelta(minutes=6) # 6 minutos atrás
    job = {
        "name": "interval",
        "cron": "interval:5m",
        "last_run": last.isoformat()
    }
    # Passou 6 mins, cron é de 5, logo DEVE rodar
    assert scheduler.should_run(job, now) is True

def test_should_run_interval_not_due():
    now = datetime(2026, 1, 1, 10, 10)
    last = now - timedelta(minutes=2) # 2 minutos atrás
    job = {
        "name": "interval",
        "cron": "interval:5m",
        "last_run": last.isoformat()
    }
    # Passou só 2 mins, DEVE retornar False
    assert scheduler.should_run(job, now) is False

def test_should_run_invalid_cron(caplog):
    import logging
    caplog.set_level(logging.ERROR)
    now = datetime.now()
    job = {
        "name": "broken",
        "cron": "interval:batata",
        "last_run": None
    }
    # Não deve subir exception, deve retornar False
    assert scheduler.should_run(job, now) is False
    assert "inválido" in caplog.text or "invalid" in caplog.text.lower()
