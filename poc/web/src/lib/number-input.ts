export interface NumberRule {
  min?: number;
  max?: number;
  integer?: boolean;
  step?: number;
  optional?: boolean;
}

export interface ParsedNumber {
  value: number | null;
  error: string | null;
}

/** Validates a typed number (accepts decimal comma); errors are shown next to the field. */
export function parseNumberInput(text: string, rule: NumberRule): ParsedNumber {
  const trimmed = text.trim().replace(",", ".");
  if (trimmed === "") {
    if (rule.optional === true) return { value: null, error: null };
    return { value: null, error: "Campo obrigatório" };
  }
  const value = Number(trimmed);
  if (Number.isNaN(value)) return { value: null, error: "Informe um número" };
  if (rule.min === 0 && value < 0) return { value: null, error: "Não pode ser negativo" };
  if (rule.min != null && value < rule.min) {
    return { value: null, error: `Mínimo ${rule.min}` };
  }
  if (rule.max != null && value > rule.max) {
    return { value: null, error: `Máximo ${rule.max}` };
  }
  if (rule.integer === true && Number.isInteger(value) === false) {
    return { value: null, error: "Informe um número inteiro" };
  }
  if (rule.step != null && Math.abs(value / rule.step - Math.round(value / rule.step)) > 1e-9) {
    return { value: null, error: `Use passos de ${String(rule.step).replace(".", ",")}` };
  }
  return { value, error: null };
}

export function numberText(value: number | null | undefined): string {
  if (value == null) return "";
  return String(value).replace(".", ",");
}
