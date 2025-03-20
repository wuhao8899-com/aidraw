import os.path

from libs.helper import *
import streamlit as st
import uuid
#数据分析的库
import pandas as pd 
import openai
#用来处理请求https的库,Response这个是用来响应https的库
from requests.models import ChunkedEncodingError
#流式组件的库
from streamlit.components import v1
#语音工具的库
from voice_toolkit import voice_toolkit

if "apibase" in st.secrets:
    openai.api_base = st.secrets["apibase"]
else:
    openai.api_base = "https://api.openai.com/v1"

st.set_page_config(
    page_title="ChatGPT Assistant",
    layout="wide",
    page_icon=ICON,
)
# 自定义元素样式
st.markdown(css_code, unsafe_allow_html=True)

if "initial_settings" not in st.session_state:
    # 历史聊天窗口
    st.session_state["path"] = "history_chats_file"
    st.session_state["history_chats"] = get_history_chats(st.session_state["path"])
    # ss参数初始化
    st.session_state["delete_dict"] = {}
    st.session_state["delete_count"] = 0
    st.session_state["voice_flag"] = ""
    st.session_state["user_voice_value"] = ""
    st.session_state["error_info"] = ""
    st.session_state["current_chat_index"] = 0
    st.session_state["user_input_content"] = ""
    # 读取全局设置
    if os.path.exists("./set.json"):
        with open("./set.json", "r", encoding="utf-8") as f:
            data_set = json.load(f)
        for key, value in data_set.items():
            st.session_state[key] = value
    # 设置完成
    st.session_state["initial_settings"] = True

with st.sidebar:
    icon_text = f"""
    <div class="icon-text-container">
        <img src='data:image/png;base64,{ICON_base64}' alt='icon'>
        <span style='font-size: 24px;'>聊天窗口</span>
    </div>
    """
    st.markdown(
        icon_text,
        unsafe_allow_html=True,
    )
    # 创建容器的目的是配合自定义组件的监听操作
    chat_container = st.container()
    with chat_container:
        # 每回返回当前选择的是谁的名字，是哪个聊天
        current_chat = st.radio(
            label="历史聊天窗口",
            format_func=lambda x: x.split("_")[0] if "_" in x else x,
            options=st.session_state["history_chats"],
            label_visibility="collapsed",
            index=st.session_state["current_chat_index"],
            key="current_chat"
            + st.session_state["history_chats"][st.session_state["current_chat_index"]],
            # on_change=current_chat_callback  # 此处不适合用回调，无法识别到窗口增减的变动
        )
    st.write("---")


# 数据写入文件
def write_data(new_chat_name=current_chat):
    if "apikey" in st.secrets:
        # 每回保留当前映射的是谁
        st.session_state["paras"] = {
            "temperature": st.session_state["temperature" + current_chat],
            "top_p": st.session_state["top_p" + current_chat],
            "presence_penalty": st.session_state["presence_penalty" + current_chat],
            "frequency_penalty": st.session_state["frequency_penalty" + current_chat],
        }
        st.session_state["contexts"] = {
            "context_select": st.session_state["context_select" + current_chat],
            "context_input": st.session_state["context_input" + current_chat],
            "context_level": st.session_state["context_level" + current_chat],
        }
        # 保存json数据
        save_data(
            st.session_state["path"],
            new_chat_name,
            st.session_state["history" + current_chat],
            st.session_state["paras"],
            st.session_state["contexts"],
        )


def reset_chat_name_fun(chat_name):
    chat_name = chat_name + "_" + str(uuid.uuid4())
    new_name = filename_correction(chat_name)
    # 下面的那个方法是st.session_state["history_chats"] = ["chat1", "chat2", "chat3"]找指定元素的方法  index = st.session_state["history_chats"].index(current_chat)
    # print(index)  # 输出 1
    current_chat_index = st.session_state["history_chats"].index(current_chat)
    st.session_state["history_chats"][current_chat_index] = new_name
    st.session_state["current_chat_index"] = current_chat_index
    # 写入新文件
    write_data(new_name)
    # 转移数据
    st.session_state["history" + new_name] = st.session_state["history" + current_chat]
    for item in [
        "context_select",
        "context_input",
        "context_level",
        #加个*是解包把这个表格的内容展开
        *initial_content_all["paras"],
    ]:
        st.session_state[item + new_name + "value"] = st.session_state[
            item + current_chat + "value"
        ]
    remove_data(st.session_state["path"], current_chat)


def create_chat_fun():
    # 合并两个表的数据
    st.session_state["history_chats"] = [
        "New Chat_" + str(uuid.uuid4())
    ] + st.session_state["history_chats"]
    st.session_state["current_chat_index"] = 0


def delete_chat_fun():
    if len(st.session_state["history_chats"]) == 1:
        chat_init = "New Chat_" + str(uuid.uuid4())
        st.session_state["history_chats"].append(chat_init)
    pre_chat_index = st.session_state["history_chats"].index(current_chat)
    if pre_chat_index > 0:
        st.session_state["current_chat_index"] = (
            st.session_state["history_chats"].index(current_chat) - 1
        )
    else:
        st.session_state["current_chat_index"] = 0
    st.session_state["history_chats"].remove(current_chat)
    remove_data(st.session_state["path"], current_chat)


with st.sidebar:
    c1, c2 = st.columns(2)
    create_chat_button = c1.button(
        "新建", use_container_width=True, key="create_chat_button"
    )
    if create_chat_button:
        create_chat_fun()
        st.rerun()

    delete_chat_button = c2.button(
        "删除", use_container_width=True, key="delete_chat_button"
    )
    if delete_chat_button:
        delete_chat_fun()
        st.rerun()

with st.sidebar:
    if ("set_chat_name" in st.session_state) and st.session_state[
        "set_chat_name"
    ] != "":
        reset_chat_name_fun(st.session_state["set_chat_name"])
        st.session_state["set_chat_name"] = ""
        st.rerun()

    st.write("\n")
    st.text_input("设定窗口名称：", key="set_chat_name", placeholder="点击输入")
    st.selectbox(
        "选择模型：",
        index=0,
        options=["gpt-4o-mini", "gpt-3.5-turbo", "gpt-4-turbo", "gpt-4o", "gpt-4"],
        key="select_model",
    )
    st.caption(
        """
    - 双击或按/键可定位输入栏
    - Ctrl + Enter 快捷提交问题
    """
    )
    st.markdown(
        '<a href="https://github.com/PierXuY/ChatGPT-Assistant" target="_blank" rel="ChatGPT-Assistant">'
        '<img src="https://badgen.net/badge/icon/GitHub?icon=github&amp;label=ChatGPT Assistant" alt="GitHub">'
        "</a>",
        unsafe_allow_html=True,
    )

# 加载数据
if "history" + current_chat not in st.session_state:
    for key, value in load_data(st.session_state["path"], current_chat).items():
        if key == "history":
            st.session_state[key + current_chat] = value
        else:
            for k, v in value.items():
                st.session_state[k + current_chat + "value"] = v

# 保证不同chat的页面层次一致，否则会导致自定义组件重新渲染
container_show_messages = st.container()
container_show_messages.write("")
# 对话展示
with container_show_messages:
    if st.session_state["history" + current_chat]:
        show_messages(current_chat, st.session_state["history" + current_chat])

# 核查是否有对话需要删除
if any(st.session_state["delete_dict"].values()):
    for key, value in st.session_state["delete_dict"].items():
        try:
            deleteCount = value.get("deleteCount")
        except AttributeError:
            deleteCount = None
        if deleteCount == st.session_state["delete_count"]:
            delete_keys = key
            st.session_state["delete_count"] = deleteCount + 1
            delete_current_chat, idr = delete_keys.split(">")
            df_history_tem = pd.DataFrame(
                st.session_state["history" + delete_current_chat]
            )
            df_history_tem.drop(
                index=df_history_tem.query("role=='user'").iloc[[int(idr)], :].index,
                inplace=True,
            )
            df_history_tem.drop(
                index=df_history_tem.query("role=='assistant'")
                .iloc[[int(idr)], :]
                .index,
                inplace=True,
            )
            st.session_state["history" + delete_current_chat] = df_history_tem.to_dict(
                "records"
            )
            write_data()
            st.rerun()


def callback_fun(arg):
    # 连续快速点击新建与删除会触发错误回调，增加判断
    if ("history" + current_chat in st.session_state) and (
        "frequency_penalty" + current_chat in st.session_state
    ):
        write_data()
        st.session_state[arg + current_chat + "value"] = st.session_state[
            arg + current_chat
        ]


def clear_button_callback():
    st.session_state["history" + current_chat] = []
    write_data()


def delete_all_chat_button_callback():
    if "apikey" in st.secrets:
        folder_path = st.session_state["path"]
        file_list = os.listdir(folder_path)
        for file_name in file_list:
            file_path = os.path.join(folder_path, file_name)
            if file_name.endswith(".json") and os.path.isfile(file_path):
                os.remove(file_path)
    st.session_state["current_chat_index"] = 0
    st.session_state["history_chats"] = ["New Chat_" + str(uuid.uuid4())]


def save_set(arg):
    st.session_state[arg + "_value"] = st.session_state[arg]
    if "apikey" in st.secrets:
        with open("./set.json", "w", encoding="utf-8") as f:
            json.dump(
                {
                    "open_text_toolkit_value": st.session_state["open_text_toolkit"],
                    "open_voice_toolkit_value": st.session_state["open_voice_toolkit"],
                },
                f,
            )


# 输入内容展示
area_user_svg = st.empty()
area_user_content = st.empty()
# 回复展示
area_gpt_svg = st.empty()
area_gpt_content = st.empty()
# 报错展示
area_error = st.empty()

st.write("\n")
st.header("ChatGPT Assistant")
tap_input, tap_context, tap_model, tab_func = st.tabs(
    ["💬 聊天", "🗒️ 预设", "⚙️ 模型", "🛠️ 功能"]
)

with tap_context:
    set_context_list = list(set_context_all.keys())
    context_select_index = set_context_list.index(
        st.session_state["context_select" + current_chat + "value"]
    )
    st.selectbox(
        label="选择提示语",
        options=set_context_list,
        key="context_select" + current_chat,
        index=context_select_index,
        on_change=callback_fun,
        args=("context_select",),
    )
    st.caption(set_context_all[st.session_state["context_select" + current_chat]])

    st.text_area(
        label="补充或自定义提示语：",
        key="context_input" + current_chat,
        value=st.session_state["context_input" + current_chat + "value"],
        on_change=callback_fun,
        args=("context_input",),
    )

with tap_model:
    st.markdown("OpenAI API Key (可选)")
    st.text_input(
        "OpenAI API Key (可选)",
        type="password",
        key="apikey_input",
        label_visibility="collapsed",
    )
    st.caption(
        "此Key仅在当前网页有效，优先级高于Secrets中的配置。[官网获取](https://platform.openai.com/account/api-keys)"
    )

    st.slider(
        "Context Level",
        0,
        10,
        st.session_state["context_level" + current_chat + "value"],
        1,
        on_change=callback_fun,
        key="context_level" + current_chat,
        args=("context_level",),
        help="表示每次会话中包含的历史对话次数，预设内容不计算在内。",
    )

    with st.expander("模型参数："):
        st.slider(
            "Temperature",
            0.0,
            2.0,
            st.session_state["temperature" + current_chat + "value"],
            0.1,
            help="""在0和2之间，应该使用什么样的采样温度？较高的值（如0.8）会使输出更随机，而较低的值（如0.2）则会使其更加集中和确定性。
              我们一般建议只更改这个参数或top_p参数中的一个，而不要同时更改两个。""",
            on_change=callback_fun,
            key="temperature" + current_chat,
            args=("temperature",),
        )
        st.slider(
            "Top P",
            0.1,
            1.0,
            st.session_state["top_p" + current_chat + "value"],
            0.1,
            help="""一种替代采用温度进行采样的方法，称为“基于核心概率”的采样。在该方法中，模型会考虑概率最高的top_p个标记的预测结果。
              因此，当该参数为0.1时，只有包括前10%概率质量的标记将被考虑。我们一般建议只更改这个参数或采样温度参数中的一个，而不要同时更改两个。""",
            on_change=callback_fun,
            key="top_p" + current_chat,
            args=("top_p",),
        )
        st.slider(
            "Presence Penalty",
            -2.0,
            2.0,
            st.session_state["presence_penalty" + current_chat + "value"],
            0.1,
            help="""该参数的取值范围为-2.0到2.0。正值会根据新标记是否出现在当前生成的文本中对其进行惩罚，从而增加模型谈论新话题的可能性。""",
            on_change=callback_fun,
            key="presence_penalty" + current_chat,
            args=("presence_penalty",),
        )
        st.slider(
            "Frequency Penalty",
            -2.0,
            2.0,
            st.session_state["frequency_penalty" + current_chat + "value"],
            0.1,
            help="""该参数的取值范围为-2.0到2.0。正值会根据新标记在当前生成的文本中的已有频率对其进行惩罚，从而减少模型直接重复相同语句的可能性。""",
            on_change=callback_fun,
            key="frequency_penalty" + current_chat,
            args=("frequency_penalty",),
        )
        st.caption(
            "[官网参数说明](https://platform.openai.com/docs/api-reference/completions/create)"
        )

with tab_func:
    c1, c2, c3 = st.columns(3)
    with c1:
        st.button(
            "清空聊天记录", use_container_width=True, on_click=clear_button_callback
        )
    with c2:
        btn = st.download_button(
            label="导出聊天记录",
            data=download_history(st.session_state["history" + current_chat]),
            file_name=f'{current_chat.split("_")[0]}.md',
            mime="text/markdown",
            use_container_width=True,
        )
    with c3:
        st.button(
            "删除所有窗口",
            use_container_width=True,
            on_click=delete_all_chat_button_callback,
        )

    st.write("\n")
    st.markdown("自定义功能：")
    c1, c2 = st.columns(2)
    with c1:
        if "open_text_toolkit_value" in st.session_state:
            default = st.session_state["open_text_toolkit_value"]
        else:
            default = True
        st.checkbox(
            "开启文本下的功能组件",
            value=default,
            key="open_text_toolkit",
            on_change=save_set,
            args=("open_text_toolkit",),
        )
    with c2:
        if "open_voice_toolkit_value" in st.session_state:
            default = st.session_state["open_voice_toolkit_value"]
        else:
            default = True
        st.checkbox(
            "开启语音输入组件",
            value=default,
            key="open_voice_toolkit",
            on_change=save_set,
            args=("open_voice_toolkit",),
        )

with tap_input:

    def input_callback():
        if st.session_state["user_input_area"] != "":
            # 修改窗口名称
            user_input_content = st.session_state["user_input_area"]
            df_history = pd.DataFrame(st.session_state["history" + current_chat])
            if df_history.empty or len(df_history.query('role!="system"')) == 0:
                new_name = extract_chars(user_input_content, 18)
                reset_chat_name_fun(new_name)

    with st.form("input_form", clear_on_submit=True):
        user_input = st.text_area(
            "**输入：**",
            key="user_input_area",
            help="内容将以Markdown格式在页面展示，建议遵循相关语言规范，同样有利于GPT正确读取，例如："
            "\n- 代码块写在三个反引号内，并标注语言类型"
            "\n- 以英文冒号开头的内容或者正则表达式等写在单反引号内",
            value=st.session_state["user_voice_value"],
        )
        submitted = st.form_submit_button(
            "确认提交", use_container_width=True, on_click=input_callback
        )
    if submitted:
        st.session_state["user_input_content"] = user_input
        st.session_state["user_voice_value"] = ""
        st.rerun()

    if (
        "open_voice_toolkit_value" not in st.session_state
        or st.session_state["open_voice_toolkit_value"]
    ):
        # 语音输入功能
        vocie_result = voice_toolkit()
        # vocie_result会保存最后一次结果
        if (
            vocie_result and vocie_result["voice_result"]["flag"] == "interim"
        ) or st.session_state["voice_flag"] == "interim":
            st.session_state["voice_flag"] = "interim"
            st.session_state["user_voice_value"] = vocie_result["voice_result"]["value"]
            if vocie_result["voice_result"]["flag"] == "final":
                st.session_state["voice_flag"] = "final"
                st.rerun()


def get_model_input():
    # 需输入的历史记录
    context_level = st.session_state["context_level" + current_chat]
    history = get_history_input(
        st.session_state["history" + current_chat], context_level
    ) + [{"role": "user", "content": st.session_state["pre_user_input_content"]}]
    for ctx in [
        st.session_state["context_input" + current_chat],
        set_context_all[st.session_state["context_select" + current_chat]],
    ]:
        if ctx != "":
            history = [{"role": "system", "content": ctx}] + history
    # 设定的模型参数
    paras = {
        "temperature": st.session_state["temperature" + current_chat],
        "top_p": st.session_state["top_p" + current_chat],
        "presence_penalty": st.session_state["presence_penalty" + current_chat],
        "frequency_penalty": st.session_state["frequency_penalty" + current_chat],
    }
    return history, paras


if st.session_state["user_input_content"] != "":
    if "r" in st.session_state:
        st.session_state.pop("r")
        st.session_state[current_chat + "report"] = ""
    st.session_state["pre_user_input_content"] = st.session_state["user_input_content"]
    st.session_state["user_input_content"] = ""
    # 临时展示
    show_each_message(
        st.session_state["pre_user_input_content"],
        "user",
        "tem",
        [area_user_svg.markdown, area_user_content.markdown],
    )
    # 模型输入
    history_need_input, paras_need_input = get_model_input()
    # 调用接口
    with st.spinner("🤔"):
        try:
            if apikey := st.session_state["apikey_input"]:
                openai.api_key = apikey
            # 配置临时apikey，此时不会留存聊天记录，适合公开使用
            elif "apikey_tem" in st.secrets:
                openai.api_key = st.secrets["apikey_tem"]
            # 注：当st.secrets中配置apikey后将会留存聊天记录，即使未使用此apikey
            else:
                openai.api_key = st.secrets["apikey"]
            r = openai.ChatCompletion.create(
                model=st.session_state["select_model"],
                messages=history_need_input,
                stream=True,
                **paras_need_input,
            )
        except (FileNotFoundError, KeyError):
            area_error.error(
                "缺失 OpenAI API Key，请在复制项目后配置Secrets，或者在模型选项中进行临时配置。"
                "详情见[项目仓库](https://github.com/PierXuY/ChatGPT-Assistant)。"
            )
        except openai.error.AuthenticationError:
            area_error.error("无效的 OpenAI API Key。")
        except openai.error.APIConnectionError as e:
            area_error.error("连接超时，请重试。报错：   \n" + str(e.args[0]))
        except openai.error.InvalidRequestError as e:
            area_error.error("无效的请求，请重试。报错：   \n" + str(e.args[0]))
        except openai.error.RateLimitError as e:
            area_error.error("请求受限。报错：   \n" + str(e.args[0]))
        else:
            st.session_state["chat_of_r"] = current_chat
            st.session_state["r"] = r
            st.rerun()

if ("r" in st.session_state) and (current_chat == st.session_state["chat_of_r"]):
    if current_chat + "report" not in st.session_state:
        st.session_state[current_chat + "report"] = ""
    try:
        for e in st.session_state["r"]:
            if "content" in e["choices"][0]["delta"]:
                st.session_state[current_chat + "report"] += e["choices"][0]["delta"][
                    "content"
                ]
                show_each_message(
                    st.session_state["pre_user_input_content"],
                    "user",
                    "tem",
                    [area_user_svg.markdown, area_user_content.markdown],
                )
                show_each_message(
                    st.session_state[current_chat + "report"],
                    "assistant",
                    "tem",
                    [area_gpt_svg.markdown, area_gpt_content.markdown],
                )
    except ChunkedEncodingError:
        area_error.error("网络状况不佳，请刷新页面重试。")
    # 应对stop情形
    except Exception:
        pass
    else:
        # 保存内容
        st.session_state["history" + current_chat].append(
            {"role": "user", "content": st.session_state["pre_user_input_content"]}
        )
        st.session_state["history" + current_chat].append(
            {"role": "assistant", "content": st.session_state[current_chat + "report"]}
        )
        write_data()
    # 用户在网页点击stop时，ss某些情形下会暂时为空
    if current_chat + "report" in st.session_state:
        st.session_state.pop(current_chat + "report")
    if "r" in st.session_state:
        st.session_state.pop("r")
        st.rerun()
        
# 添加事件监听
v1.html(js_code, height=0)
