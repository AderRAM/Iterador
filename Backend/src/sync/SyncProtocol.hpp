#pragma once

#include <string>
#include <vector>

#include "storage/OperationLog.hpp"

namespace iterador::sync {

enum class MessageType {
    Hello,
    OplogRequest,
    OplogBatch,
    Ack,
};

struct Message {
    MessageType type;
    std::string deviceId;
    std::string payloadJson;
};

// Framing e (de)serialização das mensagens trocadas entre dispositivos durante o sync (ver
// Guide/architecture.md). TODO: implementar encode/decode e o framing sobre TCP (ex. tamanho
// prefixado) junto com SyncEngine.
class SyncProtocol {
public:
    static std::string encode(const Message& message);
    static Message decode(const std::string& raw);

    static std::string encodeOplogBatch(const std::vector<storage::OperationLogEntry>& entries);
    static std::vector<storage::OperationLogEntry> decodeOplogBatch(const std::string& raw);
};

}  // namespace iterador::sync
