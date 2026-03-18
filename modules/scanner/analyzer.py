# modules/scanner/analyzer.py
from core.constants import STANDARD_PARAMS, ADDRESS_HINTS

def analyze(snapshot, references, standard_params, address_hints):
    """
    Анализирует вероятности соответствия регистров заданным ориентирам.
    snapshot: список словарей с ключами 'addr_dec', 'value_dec' и т.д.
    references: список ориентиров [{"param": "temperature", "value": 25.0, "tolerance": 1.0}]
    standard_params: словарь стандартных коэффициентов (из core.constants)
    address_hints: словарь подсказок по адресам (из core.constants)
    Возвращает словарь {addr: {param: вероятность}}.
    """
    result = {}
    if not references:
        return result

    # Для каждого параметра собираем возможные множители
    param_factors = {}
    for param, info in standard_params.items():
        base_factor = info.get("factor", 1)
        possible = [base_factor, 0.1, 0.01, 1, 10, 100]
        param_factors[param] = list(set(possible))

    for item in snapshot:
        addr = item["addr_dec"]
        raw = item["value_dec"]
        if raw is None:
            continue

        prob_dict = {}
        for ref in references:
            param = ref["param"]
            target = ref["value"]
            tolerance = ref.get("tolerance", 1.0)

            best_prob = 0.0
            for factor in param_factors.get(param, [1]):
                converted = raw * factor
                distance = abs(converted - target)
                if distance <= tolerance:
                    prob = max(0, 1 - distance / tolerance)
                else:
                    prob = 0
                if prob > best_prob:
                    best_prob = prob

            if best_prob > 0:
                prob_dict[param] = best_prob

        # Добавляем стандартные подсказки по адресам (с низким приоритетом)
        if addr in address_hints:
            for param in address_hints[addr]:
                if param not in prob_dict:
                    prob_dict[param] = 0.3  # низкая вероятность

        if prob_dict:
            result[addr] = prob_dict

    return result