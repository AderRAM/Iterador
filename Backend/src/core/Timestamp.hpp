#pragma once

#include <chrono>
#include <iomanip>
#include <sstream>
#include <string>

namespace iterador::core {

using Timestamp = std::chrono::system_clock::time_point;

inline Timestamp now() {
    return std::chrono::system_clock::now();
}

// Formata como ISO-8601 UTC, ex. "2026-09-14T12:48:00Z" — formato usado para persistir no
// SQLite e para serializar no protocolo de sync (comparável como string).
inline std::string toIso8601(const Timestamp& ts) {
    const std::time_t time = std::chrono::system_clock::to_time_t(ts);
    std::tm utcTm{};
#if defined(_WIN32)
    gmtime_s(&utcTm, &time);
#else
    gmtime_r(&time, &utcTm);
#endif
    std::ostringstream out;
    out << std::put_time(&utcTm, "%Y-%m-%dT%H:%M:%SZ");
    return out.str();
}

// Constrói um Timestamp a partir de uma data "YYYY-MM-DD" (meio-dia UTC, pra evitar que o
// dia mude por causa de fuso horário perto da virada). Usado pelo campo de data editável de
// Transaction — ver Guide/architecture.md > Roadmap sobre granularidade de data vs. hora.
inline Timestamp fromDateString(const std::string& yyyyMmDd) {
    std::tm tm{};
    std::istringstream in(yyyyMmDd);
    in >> std::get_time(&tm, "%Y-%m-%d");
    tm.tm_hour = 12;
#if defined(_WIN32)
    const std::time_t time = _mkgmtime(&tm);
#else
    const std::time_t time = timegm(&tm);
#endif
    return std::chrono::system_clock::from_time_t(time);
}

}  // namespace iterador::core
