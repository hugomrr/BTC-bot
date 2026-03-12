# 🎯 Sniper Bot MT5 — Guía de instalación

## Requisitos
- Python 3.11+
- MetaTrader 5 instalado y con cuenta activa (demo o real)
- Un bot de Telegram creado con @BotFather

## Instalación

```bash
pip install MetaTrader5 numpy python-dotenv requests
```

## Configuración

1. Copia `.env.example` como `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edita `.env` con tu token de Telegram y tu chat ID.

3. Ajusta `config.py` según tu broker:
   - `STOP_LOSS_POINTS` y `TAKE_PROFIT_POINTS` dependen del `point` de tu broker para BTCUSD
   - `MAX_SPREAD_POINTS` filtra entradas en momentos de baja liquidez
   - `MAX_SLIPPAGE_POINTS` evita ejecuciones con deslizamiento excesivo

## Ejecución

```bash
python mt5_main_bot.py
```

## Comandos Telegram disponibles

| Comando    | Descripción                        |
|------------|------------------------------------|
| `/balance` | Muestra balance, equidad y P&L     |
| `/status`  | Estado actual del bot              |
| `/help`    | Lista de comandos                  |

## Lógica de la estrategia (M1)

```
BUY  si: precio <= BB_lower  AND  RSI < 35  AND  EMA9 >= EMA21
SELL si: precio >= BB_upper  AND  RSI > 65  AND  EMA9 <= EMA21
```

El filtro EMA9/EMA21 es clave: evita entrar en rebotes contra una
tendencia fuerte, que es la causa #1 de pérdidas con BB+RSI puros.

## Máquina de estados

```
SCANNING → (señal) → IN_TRADE → (cierre) → COOLDOWN → SCANNING
              ↓ (error)
            ERROR → SCANNING
```

## .gitignore recomendado

```
.env
__pycache__/
*.pyc
```
