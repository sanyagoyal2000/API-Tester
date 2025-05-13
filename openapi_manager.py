
import streamlit as st
import requests

def load_openapi_spec():
    url_open_api_mappings = {
        "Service1": "/service1",
        "Service2": "/service2",
        "Service3": "/service3",
    }
    service_name = st.session_state.current_service
    url = f"{st.session_state.base_url}{url_open_api_mappings[service_name]}"
    response = fetch_openapi_spec(service_name, url)
    return response

def fetch_openapi_spec(service_name, base_url):
    try:
        url = f"{base_url}/openapi.json"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            spec = response.json()
            st.session_state.openapi_specs[service_name] = spec
            return spec
        else:
            st.error(f"Failed to fetch OpenAPI spec for {service_name}: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error fetching OpenAPI spec: {str(e)}")
        return None

def process_openapi_spec(openapi_spec):
    if not openapi_spec:
        return {}

    paths = openapi_spec.get("paths", {})
    tags_by_path = {}
    endpoints_by_tag = {}

    for path, methods in paths.items():
        for method, details in methods.items():
            if method.lower() in ["get", "post", "put", "delete", "patch"]:
                tags = details.get("tags", ["default"])
                tags_by_path[f"{method.upper()} {path}"] = tags[0] if tags else "default"

                for tag in tags:
                    if tag not in endpoints_by_tag:
                        endpoints_by_tag[tag] = []

                    path_params = []
                    for param in details.get("parameters", []):
                        if param.get("in") == "path":
                            path_params.append(param)

                    query_params = []
                    for param in details.get("parameters", []):
                        if param.get("in") == "query":
                            query_params.append(param)

                    request_body = details.get("requestBody", {})
                    if request_body and "content" in request_body:
                        for content_type, content_details in request_body["content"].items():
                            if "schema" in content_details and "$ref" in content_details["schema"]:
                                ref_path = content_details["schema"]["$ref"]
                                schema_name = ref_path.split("/")[-1]
                                content_details["schema"] = openapi_spec.get("components", {}).get("schemas", {}).get(schema_name, {})

                    endpoint_info = {
                        "path": path,
                        "method": method.upper(),
                        "summary": details.get("summary", ""),
                        "description": details.get("description", ""),
                        "parameters": details.get("parameters", []),
                        "path_params": path_params,
                        "query_params": query_params,
                        "requestBody": details.get("requestBody", {}),
                        "responses": details.get("responses", {}),
                        "security": details.get("security", []),
                        "fullPath": f"{method.upper()} {path}",
                    }
                    endpoints_by_tag[tag].append(endpoint_info)

    return endpoints_by_tag
