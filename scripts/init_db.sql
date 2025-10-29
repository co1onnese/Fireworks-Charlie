--
-- PostgreSQL database dump
--

\restrict sWofedOfpfgBhc9kn4i3kS5BBgWclcYxYWNGovQataiUWpYWwuctjkVQMVSRlaG

-- Dumped from database version 16.10 (Ubuntu 16.10-0ubuntu0.24.04.1)
-- Dumped by pg_dump version 16.10 (Ubuntu 16.10-0ubuntu0.24.04.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: Fundamentals; Type: TABLE; Schema: public; Owner: charlie_user
--

CREATE TABLE public."Fundamentals" (
    fundamental_id integer NOT NULL,
    ticker_id integer NOT NULL,
    report_date date NOT NULL,
    filing_date date NOT NULL,
    market_cap bigint,
    pe_ratio numeric(10,4),
    eps numeric(10,4),
    book_value numeric(18,4),
    revenue bigint,
    net_income bigint,
    total_assets bigint,
    total_liabilities bigint,
    stockholder_equity bigint,
    operating_income bigint,
    gross_profit bigint,
    balance_sheet_json json,
    income_statement_json json,
    cash_flow_json json,
    revenue_qoq_change numeric(10,4),
    net_income_qoq_change numeric(10,4),
    operating_income_qoq_change numeric(10,4),
    revenue_yoy_change numeric(10,4),
    net_income_yoy_change numeric(10,4),
    operating_income_yoy_change numeric(10,4)
);


ALTER TABLE public."Fundamentals" OWNER TO charlie_user;

--
-- Name: Fundamentals_fundamental_id_seq; Type: SEQUENCE; Schema: public; Owner: charlie_user
--

CREATE SEQUENCE public."Fundamentals_fundamental_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public."Fundamentals_fundamental_id_seq" OWNER TO charlie_user;

--
-- Name: Fundamentals_fundamental_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: charlie_user
--

ALTER SEQUENCE public."Fundamentals_fundamental_id_seq" OWNED BY public."Fundamentals".fundamental_id;


--
-- Name: Insider_Transactions; Type: TABLE; Schema: public; Owner: charlie_user
--

CREATE TABLE public."Insider_Transactions" (
    transaction_id integer NOT NULL,
    ticker_id integer NOT NULL,
    transaction_date date NOT NULL,
    owner_name character varying(255) NOT NULL,
    transaction_code character varying(10) NOT NULL,
    transaction_amount bigint,
    transaction_price numeric(18,4)
);


ALTER TABLE public."Insider_Transactions" OWNER TO charlie_user;

--
-- Name: Insider_Transactions_transaction_id_seq; Type: SEQUENCE; Schema: public; Owner: charlie_user
--

CREATE SEQUENCE public."Insider_Transactions_transaction_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public."Insider_Transactions_transaction_id_seq" OWNER TO charlie_user;

--
-- Name: Insider_Transactions_transaction_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: charlie_user
--

ALTER SEQUENCE public."Insider_Transactions_transaction_id_seq" OWNED BY public."Insider_Transactions".transaction_id;


--
-- Name: Macro_Features; Type: TABLE; Schema: public; Owner: charlie_user
--

CREATE TABLE public."Macro_Features" (
    feature_id integer NOT NULL,
    date date NOT NULL,
    yield_curve_spread numeric(5,4),
    cpi_monthly_change numeric(5,4),
    cpi_annualized_change numeric(5,4),
    pce_monthly_change numeric(5,4),
    pce_annualized_change numeric(5,4),
    gdp_quarterly_change numeric(5,4),
    industrial_production_monthly_change numeric(5,4),
    unemployment_rate_change numeric(5,4)
);


ALTER TABLE public."Macro_Features" OWNER TO charlie_user;

--
-- Name: Macro_Features_feature_id_seq; Type: SEQUENCE; Schema: public; Owner: charlie_user
--

CREATE SEQUENCE public."Macro_Features_feature_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public."Macro_Features_feature_id_seq" OWNER TO charlie_user;

--
-- Name: Macro_Features_feature_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: charlie_user
--

ALTER SEQUENCE public."Macro_Features_feature_id_seq" OWNED BY public."Macro_Features".feature_id;


--
-- Name: Macroeconomic_Indicators; Type: TABLE; Schema: public; Owner: charlie_user
--

CREATE TABLE public."Macroeconomic_Indicators" (
    macro_id integer NOT NULL,
    series_id character varying(50) NOT NULL,
    country character varying(100) NOT NULL,
    indicator_name character varying(255) NOT NULL,
    date date NOT NULL,
    value numeric(20,4) NOT NULL,
    unit character varying(100),
    frequency character varying(20)
);


ALTER TABLE public."Macroeconomic_Indicators" OWNER TO charlie_user;

--
-- Name: Macroeconomic_Indicators_macro_id_seq; Type: SEQUENCE; Schema: public; Owner: charlie_user
--

CREATE SEQUENCE public."Macroeconomic_Indicators_macro_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public."Macroeconomic_Indicators_macro_id_seq" OWNER TO charlie_user;

--
-- Name: Macroeconomic_Indicators_macro_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: charlie_user
--

ALTER SEQUENCE public."Macroeconomic_Indicators_macro_id_seq" OWNED BY public."Macroeconomic_Indicators".macro_id;


--
-- Name: News; Type: TABLE; Schema: public; Owner: charlie_user
--

CREATE TABLE public."News" (
    news_id integer NOT NULL,
    ticker_id integer NOT NULL,
    published_date timestamp without time zone NOT NULL,
    title character varying(512) NOT NULL,
    content text NOT NULL,
    sentiment character varying(50),
    sentiment_score numeric(5,2),
    days_since_last_news integer,
    url character varying(2048) NOT NULL
);


ALTER TABLE public."News" OWNER TO charlie_user;

--
-- Name: News_Features; Type: TABLE; Schema: public; Owner: charlie_user
--

CREATE TABLE public."News_Features" (
    feature_id integer NOT NULL,
    ticker_id integer NOT NULL,
    date date NOT NULL,
    sentiment_7day_avg numeric(5,2),
    sentiment_7day_count integer NOT NULL
);


ALTER TABLE public."News_Features" OWNER TO charlie_user;

--
-- Name: News_Features_feature_id_seq; Type: SEQUENCE; Schema: public; Owner: charlie_user
--

CREATE SEQUENCE public."News_Features_feature_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public."News_Features_feature_id_seq" OWNER TO charlie_user;

--
-- Name: News_Features_feature_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: charlie_user
--

ALTER SEQUENCE public."News_Features_feature_id_seq" OWNED BY public."News_Features".feature_id;


--
-- Name: News_news_id_seq; Type: SEQUENCE; Schema: public; Owner: charlie_user
--

CREATE SEQUENCE public."News_news_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public."News_news_id_seq" OWNER TO charlie_user;

--
-- Name: News_news_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: charlie_user
--

ALTER SEQUENCE public."News_news_id_seq" OWNED BY public."News".news_id;


--
-- Name: Technical_Market_Data; Type: TABLE; Schema: public; Owner: charlie_user
--

CREATE TABLE public."Technical_Market_Data" (
    tech_data_id integer NOT NULL,
    ticker_id integer NOT NULL,
    date date NOT NULL,
    "timestamp" timestamp without time zone,
    "interval" character varying(10) NOT NULL,
    open numeric(18,4) NOT NULL,
    high numeric(18,4) NOT NULL,
    low numeric(18,4) NOT NULL,
    close numeric(18,4) NOT NULL,
    adjusted_close numeric(18,4),
    volume bigint NOT NULL,
    sma numeric(18,4),
    ema numeric(18,4),
    rsi numeric(18,4),
    macd numeric(18,4),
    days_since_last_insider_trade integer
);


ALTER TABLE public."Technical_Market_Data" OWNER TO charlie_user;

--
-- Name: Technical_Market_Data_tech_data_id_seq; Type: SEQUENCE; Schema: public; Owner: charlie_user
--

CREATE SEQUENCE public."Technical_Market_Data_tech_data_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public."Technical_Market_Data_tech_data_id_seq" OWNER TO charlie_user;

--
-- Name: Technical_Market_Data_tech_data_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: charlie_user
--

ALTER SEQUENCE public."Technical_Market_Data_tech_data_id_seq" OWNED BY public."Technical_Market_Data".tech_data_id;


--
-- Name: Tickers; Type: TABLE; Schema: public; Owner: charlie_user
--

CREATE TABLE public."Tickers" (
    ticker_id integer NOT NULL,
    symbol character varying(10) NOT NULL,
    exchange character varying(10) NOT NULL,
    company_name character varying(255) NOT NULL,
    sector character varying(100),
    industry character varying(100)
);


ALTER TABLE public."Tickers" OWNER TO charlie_user;

--
-- Name: Tickers_ticker_id_seq; Type: SEQUENCE; Schema: public; Owner: charlie_user
--

CREATE SEQUENCE public."Tickers_ticker_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public."Tickers_ticker_id_seq" OWNER TO charlie_user;

--
-- Name: Tickers_ticker_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: charlie_user
--

ALTER SEQUENCE public."Tickers_ticker_id_seq" OWNED BY public."Tickers".ticker_id;


--
-- Name: Fundamentals fundamental_id; Type: DEFAULT; Schema: public; Owner: charlie_user
--

ALTER TABLE ONLY public."Fundamentals" ALTER COLUMN fundamental_id SET DEFAULT nextval('public."Fundamentals_fundamental_id_seq"'::regclass);


--
-- Name: Insider_Transactions transaction_id; Type: DEFAULT; Schema: public; Owner: charlie_user
--

ALTER TABLE ONLY public."Insider_Transactions" ALTER COLUMN transaction_id SET DEFAULT nextval('public."Insider_Transactions_transaction_id_seq"'::regclass);


--
-- Name: Macro_Features feature_id; Type: DEFAULT; Schema: public; Owner: charlie_user
--

ALTER TABLE ONLY public."Macro_Features" ALTER COLUMN feature_id SET DEFAULT nextval('public."Macro_Features_feature_id_seq"'::regclass);


--
-- Name: Macroeconomic_Indicators macro_id; Type: DEFAULT; Schema: public; Owner: charlie_user
--

ALTER TABLE ONLY public."Macroeconomic_Indicators" ALTER COLUMN macro_id SET DEFAULT nextval('public."Macroeconomic_Indicators_macro_id_seq"'::regclass);


--
-- Name: News news_id; Type: DEFAULT; Schema: public; Owner: charlie_user
--

ALTER TABLE ONLY public."News" ALTER COLUMN news_id SET DEFAULT nextval('public."News_news_id_seq"'::regclass);


--
-- Name: News_Features feature_id; Type: DEFAULT; Schema: public; Owner: charlie_user
--

ALTER TABLE ONLY public."News_Features" ALTER COLUMN feature_id SET DEFAULT nextval('public."News_Features_feature_id_seq"'::regclass);


--
-- Name: Technical_Market_Data tech_data_id; Type: DEFAULT; Schema: public; Owner: charlie_user
--

ALTER TABLE ONLY public."Technical_Market_Data" ALTER COLUMN tech_data_id SET DEFAULT nextval('public."Technical_Market_Data_tech_data_id_seq"'::regclass);


--
-- Name: Tickers ticker_id; Type: DEFAULT; Schema: public; Owner: charlie_user
--

ALTER TABLE ONLY public."Tickers" ALTER COLUMN ticker_id SET DEFAULT nextval('public."Tickers_ticker_id_seq"'::regclass);


--
-- Data for Name: Fundamentals; Type: TABLE DATA; Schema: public; Owner: charlie_user
--

COPY public."Fundamentals" (fundamental_id, ticker_id, report_date, filing_date, market_cap, pe_ratio, eps, book_value, revenue, net_income, total_assets, total_liabilities, stockholder_equity, operating_income, gross_profit, balance_sheet_json, income_statement_json, cash_flow_json, revenue_qoq_change, net_income_qoq_change, operating_income_qoq_change, revenue_yoy_change, net_income_yoy_change, operating_income_yoy_change) FROM stdin;
\.


--
-- Data for Name: Insider_Transactions; Type: TABLE DATA; Schema: public; Owner: charlie_user
--

COPY public."Insider_Transactions" (transaction_id, ticker_id, transaction_date, owner_name, transaction_code, transaction_amount, transaction_price) FROM stdin;
\.


--
-- Data for Name: Macro_Features; Type: TABLE DATA; Schema: public; Owner: charlie_user
--

COPY public."Macro_Features" (feature_id, date, yield_curve_spread, cpi_monthly_change, cpi_annualized_change, pce_monthly_change, pce_annualized_change, gdp_quarterly_change, industrial_production_monthly_change, unemployment_rate_change) FROM stdin;
\.


--
-- Data for Name: Macroeconomic_Indicators; Type: TABLE DATA; Schema: public; Owner: charlie_user
--

COPY public."Macroeconomic_Indicators" (macro_id, series_id, country, indicator_name, date, value, unit, frequency) FROM stdin;
\.


--
-- Data for Name: News; Type: TABLE DATA; Schema: public; Owner: charlie_user
--

COPY public."News" (news_id, ticker_id, published_date, title, content, sentiment, sentiment_score, days_since_last_news, url) FROM stdin;
\.


--
-- Data for Name: News_Features; Type: TABLE DATA; Schema: public; Owner: charlie_user
--

COPY public."News_Features" (feature_id, ticker_id, date, sentiment_7day_avg, sentiment_7day_count) FROM stdin;
\.


--
-- Data for Name: Technical_Market_Data; Type: TABLE DATA; Schema: public; Owner: charlie_user
--

COPY public."Technical_Market_Data" (tech_data_id, ticker_id, date, "timestamp", "interval", open, high, low, close, adjusted_close, volume, sma, ema, rsi, macd, days_since_last_insider_trade) FROM stdin;
\.


--
-- Data for Name: Tickers; Type: TABLE DATA; Schema: public; Owner: charlie_user
--

COPY public."Tickers" (ticker_id, symbol, exchange, company_name, sector, industry) FROM stdin;
\.


--
-- Name: Fundamentals_fundamental_id_seq; Type: SEQUENCE SET; Schema: public; Owner: charlie_user
--

SELECT pg_catalog.setval('public."Fundamentals_fundamental_id_seq"', 1, false);


--
-- Name: Insider_Transactions_transaction_id_seq; Type: SEQUENCE SET; Schema: public; Owner: charlie_user
--

SELECT pg_catalog.setval('public."Insider_Transactions_transaction_id_seq"', 1, false);


--
-- Name: Macro_Features_feature_id_seq; Type: SEQUENCE SET; Schema: public; Owner: charlie_user
--

SELECT pg_catalog.setval('public."Macro_Features_feature_id_seq"', 1, false);


--
-- Name: Macroeconomic_Indicators_macro_id_seq; Type: SEQUENCE SET; Schema: public; Owner: charlie_user
--

SELECT pg_catalog.setval('public."Macroeconomic_Indicators_macro_id_seq"', 1, false);


--
-- Name: News_Features_feature_id_seq; Type: SEQUENCE SET; Schema: public; Owner: charlie_user
--

SELECT pg_catalog.setval('public."News_Features_feature_id_seq"', 1, false);


--
-- Name: News_news_id_seq; Type: SEQUENCE SET; Schema: public; Owner: charlie_user
--

SELECT pg_catalog.setval('public."News_news_id_seq"', 1, false);


--
-- Name: Technical_Market_Data_tech_data_id_seq; Type: SEQUENCE SET; Schema: public; Owner: charlie_user
--

SELECT pg_catalog.setval('public."Technical_Market_Data_tech_data_id_seq"', 1, false);


--
-- Name: Tickers_ticker_id_seq; Type: SEQUENCE SET; Schema: public; Owner: charlie_user
--

SELECT pg_catalog.setval('public."Tickers_ticker_id_seq"', 1, false);


--
-- Name: Fundamentals Fundamentals_pkey; Type: CONSTRAINT; Schema: public; Owner: charlie_user
--

ALTER TABLE ONLY public."Fundamentals"
    ADD CONSTRAINT "Fundamentals_pkey" PRIMARY KEY (fundamental_id);


--
-- Name: Insider_Transactions Insider_Transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: charlie_user
--

ALTER TABLE ONLY public."Insider_Transactions"
    ADD CONSTRAINT "Insider_Transactions_pkey" PRIMARY KEY (transaction_id);


--
-- Name: Macro_Features Macro_Features_date_key; Type: CONSTRAINT; Schema: public; Owner: charlie_user
--

ALTER TABLE ONLY public."Macro_Features"
    ADD CONSTRAINT "Macro_Features_date_key" UNIQUE (date);


--
-- Name: Macro_Features Macro_Features_pkey; Type: CONSTRAINT; Schema: public; Owner: charlie_user
--

ALTER TABLE ONLY public."Macro_Features"
    ADD CONSTRAINT "Macro_Features_pkey" PRIMARY KEY (feature_id);


--
-- Name: Macroeconomic_Indicators Macroeconomic_Indicators_pkey; Type: CONSTRAINT; Schema: public; Owner: charlie_user
--

ALTER TABLE ONLY public."Macroeconomic_Indicators"
    ADD CONSTRAINT "Macroeconomic_Indicators_pkey" PRIMARY KEY (macro_id);


--
-- Name: News_Features News_Features_pkey; Type: CONSTRAINT; Schema: public; Owner: charlie_user
--

ALTER TABLE ONLY public."News_Features"
    ADD CONSTRAINT "News_Features_pkey" PRIMARY KEY (feature_id);


--
-- Name: News News_pkey; Type: CONSTRAINT; Schema: public; Owner: charlie_user
--

ALTER TABLE ONLY public."News"
    ADD CONSTRAINT "News_pkey" PRIMARY KEY (news_id);


--
-- Name: News News_url_key; Type: CONSTRAINT; Schema: public; Owner: charlie_user
--

ALTER TABLE ONLY public."News"
    ADD CONSTRAINT "News_url_key" UNIQUE (url);


--
-- Name: Technical_Market_Data Technical_Market_Data_pkey; Type: CONSTRAINT; Schema: public; Owner: charlie_user
--

ALTER TABLE ONLY public."Technical_Market_Data"
    ADD CONSTRAINT "Technical_Market_Data_pkey" PRIMARY KEY (tech_data_id);


--
-- Name: Tickers Tickers_pkey; Type: CONSTRAINT; Schema: public; Owner: charlie_user
--

ALTER TABLE ONLY public."Tickers"
    ADD CONSTRAINT "Tickers_pkey" PRIMARY KEY (ticker_id);


--
-- Name: Tickers Tickers_symbol_key; Type: CONSTRAINT; Schema: public; Owner: charlie_user
--

ALTER TABLE ONLY public."Tickers"
    ADD CONSTRAINT "Tickers_symbol_key" UNIQUE (symbol);


--
-- Name: Macroeconomic_Indicators uix_series_date; Type: CONSTRAINT; Schema: public; Owner: charlie_user
--

ALTER TABLE ONLY public."Macroeconomic_Indicators"
    ADD CONSTRAINT uix_series_date UNIQUE (series_id, date);


--
-- Name: Fundamentals Fundamentals_ticker_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: charlie_user
--

ALTER TABLE ONLY public."Fundamentals"
    ADD CONSTRAINT "Fundamentals_ticker_id_fkey" FOREIGN KEY (ticker_id) REFERENCES public."Tickers"(ticker_id);


--
-- Name: Insider_Transactions Insider_Transactions_ticker_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: charlie_user
--

ALTER TABLE ONLY public."Insider_Transactions"
    ADD CONSTRAINT "Insider_Transactions_ticker_id_fkey" FOREIGN KEY (ticker_id) REFERENCES public."Tickers"(ticker_id);


--
-- Name: News_Features News_Features_ticker_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: charlie_user
--

ALTER TABLE ONLY public."News_Features"
    ADD CONSTRAINT "News_Features_ticker_id_fkey" FOREIGN KEY (ticker_id) REFERENCES public."Tickers"(ticker_id);


--
-- Name: News News_ticker_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: charlie_user
--

ALTER TABLE ONLY public."News"
    ADD CONSTRAINT "News_ticker_id_fkey" FOREIGN KEY (ticker_id) REFERENCES public."Tickers"(ticker_id);


--
-- Name: Technical_Market_Data Technical_Market_Data_ticker_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: charlie_user
--

ALTER TABLE ONLY public."Technical_Market_Data"
    ADD CONSTRAINT "Technical_Market_Data_ticker_id_fkey" FOREIGN KEY (ticker_id) REFERENCES public."Tickers"(ticker_id);


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: pg_database_owner
--

GRANT ALL ON SCHEMA public TO charlie_user;


--
-- PostgreSQL database dump complete
--

\unrestrict sWofedOfpfgBhc9kn4i3kS5BBgWclcYxYWNGovQataiUWpYWwuctjkVQMVSRlaG

