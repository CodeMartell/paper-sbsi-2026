"""CLI: extraction, explicit local contingency or preserved-input replay."""
import argparse
import sys
from src.pipeline import execute
from src.logger import get_logger


def run(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--local', action='store_true', help='Usar arquivos locais como contingência')
    group.add_argument('--replay', help='Diretório da execução preservada')
    parser.add_argument('--policy', help='Política JSON alternativa')
    args = parser.parse_args(argv)
    folder, result = execute(local=args.local, replay=args.replay, policy_path=args.policy)
    logger = get_logger()
    logger.info("Execução %s concluída: %s; ocorrências de qualidade: %d", result['run_id'], result['state'], len(result['quality']))
    if not result['publication_allowed'] or any(p['classificacao'] == 'CRITICO' for p in result['operational']):
        logger.critical("Execução %s requer conferência; consulte os artefatos preservados.", result['run_id'])
    print(f"{result['state'].upper()}: {folder}")
    return 0 if result['publication_allowed'] else 1


if __name__ == '__main__':
    sys.exit(run())
