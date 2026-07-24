# Changelog

## 0.2.0 (Fork: computi71)

### Neu
- Werkzeug `create_time_accounting`: bucht Zeit auf einem Ticket ueber die
  Zammad-Zeiterfassung (`POST /tickets/{id}/time_accountings`). Die Zeit wird in
  der im Zammad konfigurierten Einheit angegeben (z. B. Minuten; 60 = 1 Stunde).
- Werkzeug `get_time_accountings`: liest die erfassten Zeiten eines Tickets aus
  und liefert zusaetzlich die Gesamtsumme.
- `create_article` akzeptiert optional `time_unit` (und
  `time_accounting_type_id`). Ist `time_unit` gesetzt, wird nach dem Anlegen der
  Notiz automatisch eine mit dem Artikel verknuepfte Zeitbuchung erstellt.

### Behoben
- `Article`-Modell akzeptiert jetzt auch die von der Zammad-API gelieferten
  Feldnamen (`populate_by_name=True`). Damit funktionieren `create_article` und
  `get_ticket_articles` wieder, die zuvor an `ticketId`/`ticket_id` scheiterten.

### Hinweise
- Die neuen Werkzeuge liegen in der Zugriffskategorie `tickets`. Die bestehende
  Konfiguration (`MCP_ALLOWED_CATEGORIES=tickets,groups,system`) deckt sie ab,
  es ist keine Aenderung noetig.
- Fuer das Buchen von Zeit genuegt die Token-Berechtigung `ticket.agent`.
