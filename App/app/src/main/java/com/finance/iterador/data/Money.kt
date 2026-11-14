package com.finance.iterador.data

import java.text.NumberFormat
import java.util.Locale

val PT_BR: Locale = Locale.forLanguageTag("pt-BR")

/** Formata um valor em centavos (Long, nunca float — ver Backend/src/core/Money.hpp) como "R$ 1.234,56". */
fun formatCents(cents: Long): String {
    val format = NumberFormat.getCurrencyInstance(PT_BR)
    return format.format(cents / 100.0)
}

/**
 * Converte um texto digitado pelo usuário em centavos. Aceita tanto "1234,56" (vírgula decimal,
 * ponto como separador de milhar, formato brasileiro) quanto "1234.56" (ponto decimal, sem
 * separador de milhar).
 */
fun parseCentsOrNull(text: String): Long? {
    val trimmed = text.trim()
    val normalized = if (trimmed.contains(',')) {
        trimmed.replace(".", "").replace(",", ".")
    } else {
        trimmed
    }
    val value = normalized.toDoubleOrNull() ?: return null
    return Math.round(value * 100)
}
