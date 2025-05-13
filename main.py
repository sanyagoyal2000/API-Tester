import json
import requests
from urllib.parse import urljoin
import pandas as pd
import streamlit as st

from openapi_manager import load_openapi_spec, process_openapi_spec

def initialize_session_state():
    if 'base_url' not in st.session_state:
        st.session_state.base_url = "https://test_url.com"
    if 'stoken' not in st.session_state:
        st.session_state.stoken = ""
    if 'auth_method' not in st.session_state:
        st.session_state.auth_method = "header"
    if 'selected_endpoint' not in st.session_state:
        st.session_state.selected_endpoint = None
    if 'response_data' not in st.session_state:
        st.session_state.response_data = None
    if 'response_status' not in st.session_state:
        st.session_state.response_status = None
    if 'response_headers' not in st.session_state:
        st.session_state.response_headers = None
    if 'current_service' not in st.session_state:
        st.session_state.current_service = "Service1"
    if 'custom_headers' not in st.session_state:
        st.session_state.custom_headers = [{"key": "", "value": "", "enabled": True}]
    if 'openapi_specs' not in st.session_state:
        st.session_state.openapi_specs = {}
    if 'services' not in st.session_state:
        st.session_state.services = {
            "Service1": "Service 1",
            "Service2": "Service 2",
            "Service3": "Service 3"
        }
    if 'base_url_options' not in st.session_state:
        st.session_state.base_url_options = [
            'http://127.0.0.1:5000',
            "http://127.0.0.1:8000"
        ]


def api_configuration_sidebar():
    with st.sidebar:
        st.header("Configuration")

        st.subheader("Service Selection")
        services = st.session_state.services
        full_to_short = {v: k for k, v in services.items()}
        full_names = list(full_to_short.keys())

        selected_full_name = st.selectbox(
            "Select Service",
            options=full_names,
            index=full_names.index(services[st.session_state.current_service])
            if st.session_state.get("current_service") else 0
        )

        selected_service = full_to_short[selected_full_name]

        if selected_service != st.session_state.get("current_service"):
            st.session_state.current_service = selected_service
            st.rerun()

        st.write(f"Selected Service: {selected_full_name}")

        st.subheader("API Configuration")
        current_base_url = st.session_state.get("base_url", st.session_state.base_url_options[0])

        selected_base_url = st.selectbox(
            "Select Base URL",
            st.session_state.base_url_options,
            index=st.session_state.base_url_options.index(current_base_url)
            if current_base_url in st.session_state.base_url_options else 0
        )

        new_custom_url = st.text_input("Or enter a new Base URL")

        if new_custom_url and new_custom_url != selected_base_url:
            if new_custom_url not in st.session_state.base_url_options:
                st.session_state.base_url_options.append(new_custom_url)
            st.session_state.base_url = new_custom_url
        else:
            st.session_state.base_url = selected_base_url

        st.write(f"Current Base URL: {st.session_state.base_url}")
        st.subheader("Authentication Settings")
        st.session_state.stoken = st.text_input("Auth Token", st.session_state.get("stoken", ""), type="password")
        st.session_state.auth_method = st.radio("Select Auth Method", ["header", "cookie"])

        if st.session_state.auth_method == "header":
            st.session_state.auth_header_name = st.text_input("Header Name", value="Authorization")
            st.session_state.auth_header_prefix = st.text_input("Header Prefix", value="Bearer ")
        else:
            st.session_state.auth_cookie_name = st.text_input("Cookie Name", value="stoken")



def data_partition_selection():
    st.subheader("Data Partition ID")

    partition_options = ["partition1", "partition2"]
    selected_partition = st.selectbox("Select partition ID", partition_options, index=0)
    new_partition_id = st.text_input("Or enter a new partition ID")

    if new_partition_id:
        st.session_state.data_partition_id = new_partition_id
    else:
        st.session_state.data_partition_id = selected_partition

    st.write(f"Selected Data Partition ID: {st.session_state.data_partition_id}")


def display_headers_section(key_prefix=""):
    st.subheader("Headers")
    selected_data_partition_id = ""
    headers_key = f"custom_headers_{key_prefix}"
    rerun_trigger_key = f"{key_prefix}_trigger_rerun"

    if headers_key not in st.session_state:
        st.session_state[headers_key] = [
            {"key": "data-partition-id", "value": "trial", "enabled": True},
            {"key": "", "value": "", "enabled": False}
        ]

    if rerun_trigger_key not in st.session_state:
        st.session_state[rerun_trigger_key] = False

    headers = st.session_state[headers_key]
    headers_to_remove = []

    for i, header in enumerate(headers):
        cols = st.columns([0.1, 0.35, 0.35, 0.1])

        with cols[0]:
            st.session_state[headers_key][i]["enabled"] = st.checkbox(
                "", value=header["enabled"], key=f"{key_prefix}_enabled_{i}"
            )
        with cols[1]:
            st.session_state[headers_key][i]["key"] = st.text_input(
                "Header Key", value=header["key"], key=f"{key_prefix}_key_{i}", placeholder="Content-Type"
            )
        with cols[2]:
            if headers[i]["key"] == "data-partition-id":
                partition_options = ["partition1", "partition2"]
                selected = st.selectbox("Data Partition ID for this request", partition_options,
                                        index=0, key=f"partition_{key_prefix}")
                custom = st.text_input("Or enter a custom partition ID", key=f"custom_partition_{key_prefix}")
                headers[i]["value"] = custom or selected
                selected_data_partition_id = headers[i]["value"]
            else:
                st.session_state[headers_key][i]["value"] = st.text_input(
                    "Header Value", value=header["value"], key=f"{key_prefix}_value_{i}", placeholder="application/json"
                )
        with cols[3]:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Remove", key=f"{key_prefix}_remove_{i}"):
                headers_to_remove.append(i)
                st.session_state[rerun_trigger_key] = True

    if headers_to_remove:
        for i in sorted(headers_to_remove, reverse=True):
            if i < len(headers):
                headers.pop(i)

    if st.button("Add Header", key=f"{key_prefix}_add"):
        headers.append({"key": "", "value": "", "enabled": True})
        st.session_state[rerun_trigger_key] = True

    if st.session_state[rerun_trigger_key]:
        st.session_state[rerun_trigger_key] = False
        st.rerun()

    return {h["key"]: h["value"] for h in headers if h["enabled"] and h["key"]}, selected_data_partition_id

def process_path_parameters(url_template, path_params_values):
    processed_url = url_template
    for param_name, param_value in path_params_values.items():
        if param_value:
            processed_url = processed_url.replace(f"{{{param_name}}}", str(param_value))
    return processed_url


def display_request_form(endpoint, idx):
  form_key = f"endpoint_form_{idx}"
  path_params_values = {}
  query_params_values = {}
  body_params = {}
  raw_json = ""
  json_input_type = "Form"
  custom_headers = {}
  request_partition_id = ""

  tab_labels, tab_content = build_tabs(endpoint, form_key)

  tabs = st.tabs(tab_labels)
  for label, tab in zip(tab_labels, tabs):
    with tab:
      results = tab_content[label]()
      if label == "Params":
        path_params_values, query_params_values = results
      elif label == "Headers":
        custom_headers, request_partition_id = results
      elif label == "Body":
        body_params, raw_json, json_input_type = results

  if st.button("Execute Request", key=f"execute_btn_{form_key}"):
    headers = build_headers(custom_headers, request_partition_id)

    if st.session_state.get("stoken") and st.session_state.get("auth_method") == "header":
      headers[st.session_state.auth_header_name] = (
        f"{st.session_state.auth_header_prefix}{st.session_state.stoken}"
      )

    full_path = build_full_url(endpoint["path"], path_params_values, query_params_values)

    json_data = None
    if endpoint["method"] in ["POST", "PUT", "PATCH"]:
      if json_input_type == "Raw JSON" and raw_json:
        try:
          json_data = json.loads(raw_json)
        except json.JSONDecodeError:
          st.error("Invalid JSON in request body")
          return
      else:
        json_data = prepare_request_body(body_params, endpoint)

    execute_request(endpoint, full_path, headers, json_data)

def build_tabs(endpoint, form_key):
    tab_labels = []
    tab_content = {}

    if endpoint.get("path_params") or endpoint.get("query_params"):
      tab_labels.append("Params")
      tab_content["Params"] = lambda: (
        render_path_params(endpoint, form_key),
        render_query_params(endpoint, form_key)
      )

    tab_labels.append("Headers")
    tab_content["Headers"] = lambda: render_headers_tab(form_key)

    if endpoint.get("requestBody") or endpoint["method"] in ["POST", "PUT", "PATCH"]:
      tab_labels.append("Body")
      tab_content["Body"] = lambda: render_body_tab(endpoint, form_key)

    return tab_labels, tab_content


def render_path_params(endpoint, form_key):
    values = {}
    for param in endpoint.get("path_params", []):
        name = param.get("name", "")
        ptype = param.get("schema", {}).get("type", "string")
        required = param.get("required", False)
        desc = param.get("description", "")
        key = f"path_param_{form_key}_{name}"

        if ptype == "string":
            values[name] = st.text_input(f"{name}{' (required)' if required else ''}", help=desc, key=key)
        elif ptype in ["integer", "number"]:
            values[name] = st.number_input(f"{name}{' (required)' if required else ''}", help=desc, key=key)
    return values


def render_query_params(endpoint, form_key):
    values = {}
    for param in endpoint.get("query_params", []):
        name = param.get("name", "")
        ptype = param.get("schema", {}).get("type", "string")
        required = param.get("required", False)
        desc = param.get("description", "")
        key = f"query_param_{form_key}_{name}"

        if ptype == "string":
            values[name] = st.text_input(f"{name}{' (required)' if required else ''}", help=desc, key=key)
        elif ptype in ["integer", "number"]:
            values[name] = st.number_input(f"{name}{' (required)' if required else ''}", help=desc, key=key)
        elif ptype == "boolean":
            values[name] = st.checkbox(f"{name}{' (required)' if required else ''}", help=desc, key=key)
    return values


def render_headers_tab(form_key):
    headers,request_partition_id = display_headers_section(key_prefix=f"endpoint_{form_key}")
    return headers, request_partition_id


def render_body_tab(endpoint, form_key):
    st.subheader("Enter the values for request payload either in form format or JSON format")
    request_body = endpoint.get("requestBody", {})
    method = endpoint.get("method", "GET")
    body_params = {}
    raw_json = ""
    json_input_type = "Form"
    if request_body!={} and method in ["POST", "PUT", "PATCH"]:
        content_types = list(request_body.get("content", {}).keys())
        if content_types:
            selected_content_type = st.selectbox("Content Type", content_types, index=0, key=f"content_type_{form_key}")
            if selected_content_type == "application/json":
                json_input_type = st.radio("JSON Input Type", ["Form", "Raw JSON"], key=f"json_input_type_{form_key}")
                schema = request_body.get("content", {}).get(selected_content_type, {}).get("schema", {})
                properties = schema.get("properties", {})

                if json_input_type == "Form":
                    for name, detail in properties.items():
                        ptype = detail.get("type", "string")
                        required = name in schema.get("required", [])
                        desc = detail.get("description", "")
                        body_params[name] = display_property_input(name, ptype, required, desc, key_prefix=f"body_{form_key}")
                else:
                    default_json = generate_default_json_from_schema(schema)
                    raw_json = st.text_area("JSON Body", value=json.dumps(default_json, indent=2), height=300, key=f"raw_json_{form_key}")
            else:
                raw_json = st.text_area(f"{selected_content_type} Body", value="", height=300, key=f"raw_body_{form_key}")
    elif request_body=={} and method in ["POST", "PUT", "PATCH"]:
      raw_json = st.text_area(f"JSON Body", value="", height=300,
                              key=f"raw_body_{form_key}")
      json_input_type = "Raw JSON"

    return body_params, raw_json, json_input_type


def generate_default_json_from_schema(schema):
    defaults = {}
    for name, prop in schema.get("properties", {}).items():
        ptype = prop.get("type", "string")
        if ptype == "string":
            defaults[name] = ""
        elif ptype in ["integer", "number"]:
            defaults[name] = 0
        elif ptype == "boolean":
            defaults[name] = False
        elif ptype == "array":
            defaults[name] = []
        elif ptype == "object":
            defaults[name] = {}
        else:
            defaults[name] = None
    return defaults


def build_full_url(path_template, path_params, query_params):
    path = process_path_parameters(path_template, path_params)
    query = "&".join([f"{k}={v}" for k, v in query_params.items() if v not in [None, ""]])
    return f"{path}?{query}" if query else path


def build_headers(custom_headers, partition_id):
    headers = {'Accept': 'application/json'}
    headers.update(custom_headers or {})
    headers["data-partition-id"] = partition_id
    return headers



def display_property_input(name, ptype, required, desc, key_prefix):
    key = f"{key_prefix}_{name}"
    label = f"{name}{' (required)' if required else ''}"
    if ptype == "string":
        return st.text_input(label, help=desc, key=key)
    elif ptype in ["integer", "number"]:
        return st.number_input(label, help=desc, key=key)
    elif ptype == "boolean":
        return st.checkbox(label, help=desc, key=key)
    return None

def process_path_parameters(path_template, values):
    for key, val in values.items():
        path_template = path_template.replace(f"{{{key}}}", str(val))
    return path_template

def prepare_request_body(body_params):
    return body_params


def display_property_input(prop_name, prop_type, prop_required, prop_desc, key_prefix=""):
    unique_key = f"{key_prefix}_{prop_name}"

    if prop_type == 'string':
        return st.text_input(
            f"{prop_name}{' (required)' if prop_required else ''}",
            help=prop_desc,
            key=unique_key
        )
    elif prop_type in ['number', 'integer']:
        return st.number_input(
            f"{prop_name}{' (required)' if prop_required else ''}",
            help=prop_desc,
            key=unique_key
        )
    elif prop_type == 'boolean':
        return st.checkbox(
            f"{prop_name}{' (required)' if prop_required else ''}",
            help=prop_desc,
            key=unique_key
        )
    elif prop_type == 'array':
        return st.text_area(
            f"{prop_name} (comma separated for array){' (required)' if prop_required else ''}",
            help=prop_desc,
            key=unique_key
        )
    elif prop_type == 'object':
        return st.text_area(
            f"{prop_name} (JSON object){' (required)' if prop_required else ''}",
            help=prop_desc,
            key=unique_key
        )
    return None

def display_response(response):
    st.subheader("Response")
    status_code = response.status_code
    if 200 <= status_code < 300:
        st.success(f"Status: {status_code}")
    elif 300 <= status_code < 400:
        st.info(f"Status: {status_code}")
    elif 400 <= status_code < 500:
        st.warning(f"Status: {status_code}")
    else:
        st.error(f"Status: {status_code}")

    response_header_tab, response_body_tab = st.tabs(["Headers", "Body"])

    with response_header_tab:
        for header, value in response.headers.items():
            st.write(f"**{header}:** {value}")

    with response_body_tab:
        try:
            resp_json = response.json()
            st.json(resp_json)
        except json.JSONDecodeError:
            st.text(response.text)

def prepare_request_body(body_params, endpoint):
    if not body_params:
        return {}

    json_data = {}
    for param_name, param_value in body_params.items():
        if param_value is not None and param_value != "":
            json_data[param_name] = process_param_value(param_name, param_value, endpoint)
    return json_data

def process_param_value(param_name, param_value, endpoint):
    request_body = endpoint.get('requestBody', {})
    content = request_body.get('content', {}).get('application/json', {})
    schema = content.get('schema', {})
    properties = schema.get('properties', {})
    prop_type = properties.get(param_name, {}).get('type', 'string')

    if prop_type == 'array' and isinstance(param_value, str):
        return [item.strip() for item in param_value.split(',')]
    elif prop_type == 'object' and isinstance(param_value, str):
        try:
            return json.loads(param_value)
        except json.JSONDecodeError:
            return param_value
    elif prop_type == 'number':
        try:
            return float(param_value)
        except (TypeError, ValueError):
            return param_value
    elif prop_type == 'integer':
        try:
            return int(param_value)
        except (TypeError, ValueError):
            return param_value
    elif prop_type == 'boolean' and isinstance(param_value, str):
        return param_value.lower() in ('true', 'yes', '1', 'y')

    return param_value


def execute_request(endpoint, path, headers, json_data):
    try:
        url = urljoin(st.session_state.base_url, path)
        cookies = {}
        if st.session_state.stoken and st.session_state.auth_method == "cookie":
            cookies[st.session_state.auth_cookie_name] = st.session_state.stoken

        st.subheader("Request Details")
        st.markdown(f"**URL:** {url}")
        st.markdown(f"**Method:** {endpoint['method']}")

        st.subheader("Headers")
        st.json(headers)

        if json_data and endpoint['method'] in ['POST', 'PUT', 'PATCH']:
            st.subheader("Request Body")
            st.json(json_data)

        with st.spinner(f"Executing {endpoint['method']} request..."):
            response = send_request(endpoint['method'], url, headers, cookies, json_data)
        display_response(response)

    except Exception as e:
        st.error(f"Error executing request: {str(e)}")

def display_endpoints(endpoints_by_tag):
    if not endpoints_by_tag:
        st.warning("No endpoints available. Please check your connection to the API server.")
        return

    sorted_tags = sorted(endpoints_by_tag.keys())
    for tag in sorted_tags:
        st.header(f"{tag}")
        endpoint_data = [{"Method": endpoint["method"], "Path": endpoint["path"], "Summary": endpoint["summary"]} for endpoint in endpoints_by_tag[tag]]
        df = pd.DataFrame(endpoint_data)
        st.dataframe(df, use_container_width=True)

        for idx, endpoint in enumerate(endpoints_by_tag[tag]):
            with st.expander(f"{endpoint['method']} {endpoint['path']} - {endpoint['summary']}"):
                st.write(f"**Description** {endpoint.get('description', 'No description provided')}")
                display_request_form(endpoint, f"{tag}_{idx}")

def send_request(method, url, headers, cookies, json_data):
    if method == 'GET':
        return requests.get(url=url, headers=headers, cookies=cookies, timeout=30)
    elif method == 'POST':
        return requests.post(url=url, json=json_data, headers=headers, cookies=cookies, timeout=30)
    elif method == 'PUT':
        return requests.put(url=url, json=json_data, headers=headers, cookies=cookies, timeout=30)
    elif method == 'DELETE':
        return requests.delete(url=url, headers=headers, cookies=cookies, timeout=30)
    elif method == 'PATCH':
        return requests.patch(url=url, json=json_data, headers=headers, cookies=cookies, timeout=30)
    else:
        raise ValueError(f"Unsupported HTTP method: {method}")

def main():
    st.set_page_config(layout="wide", page_title="API Tester")

    st.title("APIs Tester")

    initialize_session_state()
    api_configuration_sidebar()

    with st.spinner("Loading OpenAPI specification..."):
        openapi_spec = load_openapi_spec()

    if openapi_spec:
        tags = process_openapi_spec(openapi_spec)
        display_endpoints(tags)
    else:
        st.warning("Unable to load OpenAPI specification. Please check the base URL and try again.")

if __name__ == "__main__":
    main()
