#include <sstream>
#include <iomanip>

#include "util.h"

namespace util 
{
    /* Escape a json string */
    /* Courtesy: https://stackoverflow.com/a/19636328 */
    std::string escape_json(const std::string& input)
    {
        std::string output;
        output.reserve(input.length());

        for (std::string::size_type i = 0; i < input.length(); ++i)
        {
            switch (input[i]) {
                case '"':
                    output += "\\\"";
                    break;
                case '/':
                    output += "\\/";
                    break;
                case '\b':
                    output += "\\b";
                    break;
                case '\f':
                    output += "\\f";
                    break;
                case '\n':
                    output += "\\n";
                    break;
                case '\r':
                    output += "\\r";
                    break;
                case '\t':
                    output += "\\t";
                    break;
                case '\\':
                    output += "\\\\";
                    break;
                default:
                    output += input[i];
                    break;
            }
        }

        return output;
    }

    /* Unescape a json string */
    /* Courtesy: https://stackoverflow.com/a/19636328 */
    std::string unescape_json(const std::string& input)
    {
        bool escaped = false;
        std::string output;
        output.reserve(input.length());

        for (std::string::size_type i = 0; i < input.length(); ++i)
        {
            switch(escaped)
            {
                case true:
                    {
                        switch(input[i])
                        {
                            case '"':
                                output += '\"';
                                break;
                            case '/':
                                output += '/';
                                break;
                            case 'b':
                                output += '\b';
                                break;
                            case 'f':
                                output += '\f';
                                break;
                            case 'n':
                                output += '\n';
                                break;
                            case 'r':
                                output += '\r';
                                break;
                            case 't':
                                output += '\t';
                                break;
                            case '\\':
                                output += '\\';
                                break;
                            default:
                                output += input[i];
                                break;
                        }

                        escaped = false;
                        break;
                    }
                case false:
                    {
                        switch(input[i])
                        {
                            case '\\':
                                escaped = true;
                                break;
                            default:
                                output += input[i];
                                break;
                        }
                    }
            }
        }
        return output;
    }
}