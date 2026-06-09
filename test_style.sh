#!/bin/bash
sed -i '784,814c\
/* Header Restructure for All Screen Sizes */\
.name-watchlist-row {\
    display: grid;\
    grid-template-columns: auto 1fr auto;\
    grid-template-areas: \
        "chart ticker star"\
        "name name name";\
    gap: 15px 10px;\
    align-items: center;\
    width: 100%;\
    padding: 0 10px;\
}\
.chart-col { grid-area: chart; }\
.ticker-col {\
    grid-area: ticker;\
    text-align: center;\
    display: flex;\
    justify-content: center;\
    align-items: center;\
}\
.ticker-col .ticker {\
    font-size: 1.3rem;\
    font-weight: bold;\
}\
.star-col { grid-area: star; }\
.name-col {\
    grid-area: name;\
    text-align: center;\
    margin-top: 5px;\
    white-space: nowrap;\
}\
.name-col h2 {\
    margin: 0;\
}\
\
@media (max-width: 768px) {\
    .name-col h2 { font-size: 1.25rem !important; }\
}' style.css
