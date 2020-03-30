#include <sstream>
#include <iomanip>

#include "util.h"

namespace util 
{
    /* Escape a json string */
    std::string escape_json(const std::string &s) {
        std::ostringstream o;
        for (auto c = s.cbegin(); c != s.cend(); c++) {
            switch (*c) {
            case '"': o << "\\\""; break;
            case '\\': o << "\\\\"; break;
            case '\b': o << "\\b"; break;
            case '\f': o << "\\f"; break;
            case '\n': o << "\\n"; break;
            case '\r': o << "\\r"; break;
            case '\t': o << "\\t"; break;
            default:
                if ('\x00' <= *c && *c <= '\x1f') {
                    o << "\\u"
                    << std::hex << std::setw(4) << std::setfill('0') << (int)*c;
                } else {
                    o << *c;
                }
            }
        }
        return o.str();
    }

    /* Escape a json string and add quotes */
    std::string escape_json_add_quotes(const std::string &s) {
        std::string ostr = "\"";
        ostr += escape_json(s);
        return ostr + "\"";
    }
}