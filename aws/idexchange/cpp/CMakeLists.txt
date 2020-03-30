cmake_minimum_required(VERSION 3.5)
set(CMAKE_CXX_STANDARD 11)
project(hello LANGUAGES CXX)

find_package(aws-lambda-runtime REQUIRED)
include_directories(${PROJECT_SOURCE_DIR})
add_executable(${PROJECT_NAME} "main.cpp" "util.cpp" "ttest.cpp" "RSJparser.tcc")
target_link_libraries(${PROJECT_NAME} PUBLIC AWS::aws-lambda-runtime)
aws_lambda_package_target(${PROJECT_NAME})