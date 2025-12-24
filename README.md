# Reference Catalog of Data Quality Requirement Patterns
The Reference catalog of Data Quality Requirement (DQR) Patterns is designed to support Data Space Governance Authorities in defining and managing data quality throughout the governance and operational processes underpinning their data spaces. It enables authorities to elicit DQRs by selecting and instantiating relevant patterns, thereby constructing a data space specific DQR catalog tailored to their governance and operational needs. 

These patterns capture common and recurring DQRs encountered in data space data sharing and governance scenarios. For each pattern in the catalog, the associated data quality dimension, its identifier, a textual description of the requirement, the pattern template, and an example of the pattern instatiation are explicitly defined.


| Quality Dimension | DQR Pattern Identifier | DQR Description | DQR Pattern | DQR Pattern Instantiation Example |
| ----------------- | ---------------------- | --------------- | ----------- | ----------------------------------|
| Timeless (ISO/IEC 25012)| DQRP1 | A specific data age is required for the data in an attribute of an entity | [DQRP1](https://github.com/feed-upc/DS-DataQualityRequirements/blob/main/media/DQRP1-Timeless.png)| A hypothetical financial data space performs the [DQRP1 Instantiation](https://github.com/feed-upc/DS-DataQualityRequirements/blob/main/media/DQRP1Instantiation.png) to define a DQR for specifying that live stock prices are valid only if their data age does not exceed 30 minutes. Its corresponding ODRL rule is [DQRP1ODRLRule](https://github.com/feed-upc/DS-DataQualityRequirements/blob/main/media/DQRP1ODRLRule.png)|
