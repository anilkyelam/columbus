#ifndef UTIL_H
#define UTIL_H

namespace util
{
    std::string escape_json(const std::string &s);
    std::string escape_json_add_quotes(const std::string &s);
}

#endif /* UTIL_H */