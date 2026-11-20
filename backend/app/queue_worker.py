"""Supervisor de processos consumidores da fila Redis de triagem."""

import logging
import multiprocessing
import os
import signal
import time


logger = logging.getLogger("mediflow.triagem_worker")


def _executar_worker(indice: int) -> None:
    # Cada processo cria sua própria conexão Redis e consome um job por vez.
    from redis import Redis
    from rq import Queue, Worker

    from app.config.settings import settings
    from app.services.triagem_queue import NOME_FILA_TRIAGEM

    connection = Redis.from_url(settings.REDIS_URL)
    fila = Queue(NOME_FILA_TRIAGEM, connection=connection)
    Worker(
        [fila],
        connection=connection,
        name=f"triagem-worker-{indice}",
    ).work(with_scheduler=False)


def main() -> None:
    try:
        concorrencia = int(os.getenv("TRIAGEM_WORKER_CONCURRENCY", "5"))
    except ValueError as erro:
        raise ValueError("TRIAGEM_WORKER_CONCURRENCY precisa ser um inteiro positivo.") from erro
    if concorrencia < 1:
        raise ValueError("TRIAGEM_WORKER_CONCURRENCY precisa ser maior que zero.")

    contexto = multiprocessing.get_context("spawn")
    encerrando = contexto.Event()

    def solicitar_encerramento(_sinal, _frame):
        encerrando.set()

    signal.signal(signal.SIGTERM, solicitar_encerramento)
    signal.signal(signal.SIGINT, solicitar_encerramento)

    processos: dict[int, multiprocessing.Process] = {}

    def iniciar(indice: int) -> None:
        processo = contexto.Process(
            target=_executar_worker,
            args=(indice,),
            name=f"triagem-worker-{indice}",
        )
        processo.start()
        processos[indice] = processo

    for indice in range(1, concorrencia + 1):
        iniciar(indice)

    logger.info("Workers de triagem ativos: %s processos no mesmo container", concorrencia)
    try:
        while not encerrando.wait(1):
            for indice, processo in list(processos.items()):
                if not processo.is_alive():
                    codigo_saida = processo.exitcode
                    processo.join()
                    logger.error(
                        "Processo triagem-worker-%s encerrou (exit=%s); reiniciando",
                        indice,
                        codigo_saida,
                    )
                    if not encerrando.is_set():
                        iniciar(indice)
    finally:
        for processo in processos.values():
            if processo.is_alive():
                processo.terminate()
        for processo in processos.values():
            processo.join(timeout=10)


if __name__ == "__main__":
    main()
