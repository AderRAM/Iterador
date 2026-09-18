#include "sync/SyncProtocol.hpp"

#include <stdexcept>

namespace iterador::sync {

std::string SyncProtocol::encode(const Message&) {
    throw std::logic_error("SyncProtocol::encode ainda nao implementado");
}

Message SyncProtocol::decode(const std::string&) {
    throw std::logic_error("SyncProtocol::decode ainda nao implementado");
}

std::string SyncProtocol::encodeOplogBatch(const std::vector<storage::OperationLogEntry>&) {
    throw std::logic_error("SyncProtocol::encodeOplogBatch ainda nao implementado");
}

std::vector<storage::OperationLogEntry> SyncProtocol::decodeOplogBatch(const std::string&) {
    throw std::logic_error("SyncProtocol::decodeOplogBatch ainda nao implementado");
}

}  // namespace iterador::sync
