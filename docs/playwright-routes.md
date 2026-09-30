# Application route inventory

Source-derived route records; JSON includes parameters, redirects, templates, decorators and view line numbers.
Decorators describe observed code, not a claim that access control is sufficient. No custom Django forms, DRF routers or viewsets were found.

| App | Route | Name | View | Methods | Access | Templates |
|---|---|---|---|---|---|---|
| home | `/` | home | index | No method decorator | Broker_only | index.html |
| home | `/indexforCustomer` | homeforcustomer | indexforCustomer | No method decorator | allowed_users(allowed_roles=['Customer']) | index.html |
| home | `/<str:IPOid>/<str:OrderType>/update_pann/<str:GrpName>/<str:OrderCategory>/<str:InvestorType>` | OrderDetail_update | Update_pann | No method decorator | No explicit decorator; inspect view/session checks |  |
| home | `/clear-selected-records/` | clear_selected_records | ClearSelectedRecords | POST branch; other verbs not necessarily rejected | No explicit decorator; inspect view/session checks |  |
| home | `/ChangePassword` | ChangePassword | ChangePassword | POST branch; other verbs not necessarily rejected | allowed_users(allowed_roles=['Broker']) | index.html |
| home | `/get-options/` | get_options | get_options | No method decorator | No explicit decorator; inspect view/session checks |  |
| home | `/<str:IPOid>/get-rates/<str:Ordtyp>` | get_rates_json | get_rates_json | No method decorator | No explicit decorator; inspect view/session checks |  |
| home | `/<str:IPOid>/<str:OrderType>/IPO_Allotment/<str:group>/<str:IPOType>/<str:InvestType>` |  | IPO_Allotment | POST branch; other verbs not necessarily rejected | No explicit decorator; inspect view/session checks |  |
| home | `/<str:IPOid>/<str:OrderType>/IPO_Allotment/<str:group>/<str:IPOType>/<str:InvestType>/<str:Rate>` | get_options | IPO_Allotment | POST branch; other verbs not necessarily rejected | No explicit decorator; inspect view/session checks |  |
| home | `/get_pancards/<str:IPOid>/<str:OrderType>/<str:group>/<str:IPOType>/<str:InvestType>` |  | get_pancards | POST branch; other verbs not necessarily rejected | No explicit decorator; inspect view/session checks |  |
| home | `/get_pancards/<str:IPOid>/<str:OrderType>/<str:group>/<str:IPOType>/<str:InvestType>/<str:Rate>` | get_pancards | get_pancards | POST branch; other verbs not necessarily rejected | No explicit decorator; inspect view/session checks |  |
| home | `/ChangeUserpassword` | ChangeUserpassword | Changepassword | POST branch; other verbs not necessarily rejected | allowed_users(allowed_roles=['Broker']) | index.html |
| home | `/IPOSETUP` | IPOSETUP | IPOSETUP | POST branch; other verbs not necessarily rejected | allowed_users(allowed_roles=['Broker']) | IPOSETUP.html |
| home | `/ClientSetup` | ClientSetup | ClientSetup | POST branch; other verbs not necessarily rejected | allowed_users(allowed_roles=['Broker']) | ClientSetup.html |
| home | `/ClientSetup/<str:PanNoId>` | ClientSetup | ClientSetup | POST branch; other verbs not necessarily rejected | allowed_users(allowed_roles=['Broker']) | ClientSetup.html |
| home | `/GroupSetup` | GroupSetup | GroupSetup | POST branch; other verbs not necessarily rejected | allowed_users(allowed_roles=['Broker']) | GroupSetup.html |
| home | `/AddCustomerUser` | AddCustomerUser | AddCustomerUser | POST branch; other verbs not necessarily rejected | allowed_users(allowed_roles=['Broker']) | AddCustomerUser.html |
| home | `/AddIPO` | AddIPO | AddIPO | POST branch; other verbs not necessarily rejected | allowed_users(allowed_roles=['Broker']) |  |
| home | `/AddClient` | AddClient | AddClient | POST branch; other verbs not necessarily rejected | allowed_users(allowed_roles=['Broker']) |  |
| home | `/AddGroup` | AddGroup | AddGroup | POST branch; other verbs not necessarily rejected | allowed_users(allowed_roles=['Broker']) |  |
| home | `/ErrorCSV` | ErrorCSV | Error_csv | POST branch; other verbs not necessarily rejected | No explicit decorator; inspect view/session checks |  |
| home | `/AddGroup/<str:IPOid>/<str:Action>` | AddGroupFromPlaceOrder | AddGroupFromPlaceOrder | POST branch; other verbs not necessarily rejected | allowed_users(allowed_roles=['Broker']) |  |
| home | `/BulkUploadGroup` | BulkUploadGroup | BulkUploadGroup | No method decorator | allowed_users(allowed_roles=['Broker']) |  |
| home | `/DownloadGroupSample` | DownloadGroupSample | DownloadGroupSample | No method decorator | allowed_users(allowed_roles=['Broker']) |  |
| home | `/edit/<str:IPOid>` |  | edit | No method decorator | allowed_users(allowed_roles=['Broker']) | edit.html |
| home | `/EditClient/<str:PanNoId>` |  | EditClient | No method decorator | allowed_users(allowed_roles=['Broker']) | EditClient.html |
| home | `/EditGroup/<str:GroupNameId>` |  | EditGroup | No method decorator | allowed_users(allowed_roles=['Broker']) | EditGroup.html |
| home | `/update/<str:IPOid>` |  | update | POST branch; other verbs not necessarily rejected | allowed_users(allowed_roles=['Broker']) | edit.html |
| home | `/<str:IPOid>/updatepreopenprice/<str:group>/<str:IPOType>/<str:InvestType>` |  | updatepreopenprice | POST branch; other verbs not necessarily rejected | allowed_users(allowed_roles=['Broker']) |  |
| home | `/<str:IPOid>/<str:OrderDetailId>/EditOrderPreOpenPrice/<str:OrderCategory>/<str:InvestorType>/<str:group>/<str:IPOType>/<str:InvestType>` |  | EditOrderPreOpenPrice | POST branch; other verbs not necessarily rejected | No explicit decorator; inspect view/session checks |  |
| home | `/UpdateClient/<str:PANNoId>` |  | UpdateClient | POST branch; other verbs not necessarily rejected | allowed_users(allowed_roles=['Broker']) | EditClient.html |
| home | `/UpdateGroup/<str:GroupNameId>` |  | UpdateGroup | POST branch; other verbs not necessarily rejected | allowed_users(allowed_roles=['Broker']) | EditGroup.html |
| home | `/delete/<int:IPOid>` | destroy | destroy | No method decorator | allowed_users(allowed_roles=['Broker']) |  |
| home | `/DeleteClient/<str:PANNoId>` |  | DeleteClient | No method decorator | allowed_users(allowed_roles=['Broker']) |  |
| home | `/DeleteAllClient` |  | DeleteAllClient | No method decorator | allowed_users(allowed_roles=['Broker']) |  |
| home | `/DeleteGroup/<str:GroupNameId>` |  | DeleteGroup | No method decorator | allowed_users(allowed_roles=['Broker']) |  |
| home | `/DeleteOrder/<str:IPOid>/<str:OrderId>/<str:GrpName>/<str:OrderCategory>/<str:InvestorType>` |  | DeleteOrder | No method decorator | allowed_users(allowed_roles=['Broker']) |  |
| home | `/<str:IPOid>/SetRate` |  | SetRate | POST branch; other verbs not necessarily rejected | allowed_users(allowed_roles=['Broker']) | SetRate.html |
| home | `/<str:IPOid>/BUY` |  | BUY | POST branch; other verbs not necessarily rejected | allowed_users(allowed_roles=['Broker', 'Customer']) | buy.html |
| home | `/BUY/<str:IPOid>/<str:selectgroup>` |  | BUY | POST branch; other verbs not necessarily rejected | allowed_users(allowed_roles=['Broker', 'Customer']) | buy.html |
| home | `/<str:IPOid>/SELL` |  | sell | POST branch; other verbs not necessarily rejected | allowed_users(allowed_roles=['Broker', 'Customer']) | sell.html |
| home | `/SELL/<str:IPOid>/<str:selectgroup>` |  | sell | POST branch; other verbs not necessarily rejected | allowed_users(allowed_roles=['Broker', 'Customer']) | sell.html |
| home | `/<str:IPOid>/Order` |  | OrderFunction | POST branch; other verbs not necessarily rejected | allowed_users(allowed_roles=['Broker', 'Customer']) | Order.html |
| home | `/<str:IPOid>/EditOrder/<str:OrderId>/<str:Grpf>/<str:OrCtf>/<str:InTyf>` |  | EditOrder | No method decorator | No explicit decorator; inspect view/session checks | EditOrder.html |
| home | `/<str:IPOid>/<str:OrderId>/UpdateOrder/<str:Grpf>/<str:OrCtf>/<str:InTyf>` |  | UpdateOrder | POST branch; other verbs not necessarily rejected | allowed_users(allowed_roles=['Broker']) |  |
| home | `/<str:IPOid>/<str:OrderId>/EditOrderRate/<str:GrpName>/<str:OrderCategory>/<str:InvestorType>` |  | EditOrderRate | POST branch; other verbs not necessarily rejected | allowed_users(allowed_roles=['Broker']) |  |
| home | `/<str:IPOid>/OrderDetail/<str:Ordtyp>` |  | OrderDetailFunction | POST branch; other verbs not necessarily rejected | No explicit decorator; inspect view/session checks | OrderDetail - Sell.html, OrderDetail.html |
| home | `/<str:IPOid>/OrderDetail/<str:Ordtyp>/<str:GrpName>/<str:OrderCategory>/<str:InvestorType>` |  | OrderDetailFunction | POST branch; other verbs not necessarily rejected | No explicit decorator; inspect view/session checks | OrderDetail - Sell.html, OrderDetail.html |
| home | `/<str:IPOid>/OrderDetail/<str:Ordtyp>/<str:GrpName>/<str:OrderCategory>/<str:InvestorType>/<str:OrderDate>/<str:OrderTime>` |  | OrderDetailFunction | POST branch; other verbs not necessarily rejected | No explicit decorator; inspect view/session checks | OrderDetail - Sell.html, OrderDetail.html |
| home | `/<str:IPOid>/OrderDetail/<str:Ordtyp>/<str:GrpName>/<str:OrderCategory>/<str:InvestorType>/<str:OrderDate>/<str:OrderTime>/<str:Rate>` |  | OrderDetailFunction | POST branch; other verbs not necessarily rejected | No explicit decorator; inspect view/session checks | OrderDetail - Sell.html, OrderDetail.html |
| home | `/<str:IPOid>/Order/<str:Groupfilter>/<str:OrderCategoryFilter>/<str:InvestorTypeFilter>` |  | filterfromstatus | POST branch; other verbs not necessarily rejected | allowed_users(allowed_roles=['Broker', 'Customer']) | Order.html |
| home | `/<str:IPOid>/<str:OrderType>/AddPan-<str:OrderDetailId>/<str:GrpName>/<str:OrderCategory>/<str:InvestorType>/<str:OrderDate>/<str:OrderTime>` | AddPan | AddPan | POST branch; other verbs not necessarily rejected | allowed_users(allowed_roles=['Broker', 'Customer']) |  |
| home | `/<str:IPOid>/<str:OrderType>/FirmAllotment/<str:GrpName>/<str:OrderCategory>/<str:InvestorType>` |  | FirmAllotment | POST branch; other verbs not necessarily rejected | allowed_users(allowed_roles=['Broker', 'Customer']) |  |
| home | `/<str:IPOid>/<str:OrderType>/FirmAllotment/<str:GrpName>/<str:OrderCategory>/<str:InvestorType>/<str:Rate>` | FirmAllotment | FirmAllotment | POST branch; other verbs not necessarily rejected | allowed_users(allowed_roles=['Broker', 'Customer']) |  |
| home | `/autocomplete` | autocomplete | autocomplete | No method decorator | allowed_users(allowed_roles=['Broker']) |  |
| home | `/autocomplete1` | autocomplete1 | autocomplete1 | POST branch; other verbs not necessarily rejected | allowed_users(allowed_roles=['Broker']) |  |
| home | `/<str:IPOid>/Billing` | Billing | Billing | POST branch; other verbs not necessarily rejected | allowed_users(allowed_roles=['Broker', 'Customer']) | Billing.html |
| home | `/<str:IPOid>/Billing/<str:group>/<str:IPOType>/<str:InvestType>` |  | FileterBilling | POST branch; other verbs not necessarily rejected | No explicit decorator; inspect view/session checks | Billing.html |
| home | `/<str:IPOid>/Billing/<str:group>/<str:IPOType>/<str:InvestType>/<str:Rate>` | Billing | FileterBilling | POST branch; other verbs not necessarily rejected | No explicit decorator; inspect view/session checks | Billing.html |
| home | `/<str:IPOid>/download-Billing/<str:group>/<str:IPOType>/<str:InvestorType>` | exportBillingFilter | exportBillingFilter | No method decorator | allowed_users(allowed_roles=['Broker']) |  |
| home | `/download-Groupwise` | exportBillingFilter | exportGroupwise | No method decorator | No explicit decorator; inspect view/session checks |  |
| home | `/<str:IPOid>/Sempale-Order` | Sempale-Order | Sempale_Order | No method decorator | No explicit decorator; inspect view/session checks |  |
| home | `/<str:IPOid>/download-Billing-Pdf/<str:group>/<str:IPOType>/<str:InvestorType>` | exportBillingFilterpdf | exportBillingFilterpdf | No method decorator | No explicit decorator; inspect view/session checks |  |
| home | `/<str:IPOid>/Backup/` | Backup | Backup | No method decorator | allowed_users(allowed_roles=['Broker']) |  |
| home | `/AllIpoBackup` | AllIpoBackup | AllIpoBackup | No method decorator | No explicit decorator; inspect view/session checks |  |
| home | `/<str:IPOid>/download-csv/<str:OrderType>/<str:group>/<str:IPOType>/<str:InvestorType>/<str:OrderDate>/<str:OrderTime>` |  | export | No method decorator | No explicit decorator; inspect view/session checks |  |
| home | `/<str:IPOid>/download-csv/<str:OrderType>/<str:group>/<str:IPOType>/<str:InvestorType>/<str:OrderDate>/<str:OrderTime>/<str:Rate>` | OrderDetail_download | export | No method decorator | No explicit decorator; inspect view/session checks |  |
| home | `/<str:IPOid>/Group_wise-download-csv/<str:OrderType>/<str:IPOType>/<str:InvestorType>/<str:OrderDate>/<str:OrderTime>` |  | Group_wise_export | No method decorator | allowed_users(allowed_roles=['Broker', 'Customer']) |  |
| home | `/<str:IPOid>/Group_wise-download-csv/<str:OrderType>/<str:IPOType>/<str:InvestorType>/<str:OrderDate>/<str:OrderTime>/<str:Rate>` | OrderDetail_download | Group_wise_export | No method decorator | allowed_users(allowed_roles=['Broker', 'Customer']) |  |
| home | `/<str:IPOid>/Dashboard/<str:value>` | Dashboard | dashboard | No method decorator | allowed_users(allowed_roles=['Broker']) | Bdashboard.html, Bdashboard_sme.html, Cdashboard.html, Cdashboard_sme.html, dashboard.html, dashboard_sme.html |
| home | `/<str:IPOid>/DashboardForm/<str:value>` | DashboardForm | dashboardform | POST branch; other verbs not necessarily rejected | allowed_users(allowed_roles=['Broker']) |  |
| home | `/<str:IPOid>/download-AllRecords-csv/<str:OrderType>/<str:group>/<str:IPOType>/<str:InvestorType>/<str:OrderDate>/<str:OrderTime>` |  | exportall | No method decorator | No explicit decorator; inspect view/session checks |  |
| home | `/<str:IPOid>/download-AllRecords-csv/<str:OrderType>/<str:group>/<str:IPOType>/<str:InvestorType>/<str:OrderDate>/<str:OrderTime>/<str:Rate>` | OrderDetail_download_AllRecords | exportall | No method decorator | No explicit decorator; inspect view/session checks |  |
| home | `/<str:IPOid>/Group_wise-download-AllRecords-csv/<str:OrderType>/<str:IPOType>/<str:InvestorType>/<str:OrderDate>/<str:OrderTime>` |  | Group_wise_exportall | No method decorator | allowed_users(allowed_roles=['Broker', 'Customer']) |  |
| home | `/<str:IPOid>/Group_wise-download-AllRecords-csv/<str:OrderType>/<str:IPOType>/<str:InvestorType>/<str:OrderDate>/<str:OrderTime>/<str:Rate>` | OrderDetail_download_AllRecords | Group_wise_exportall | No method decorator | allowed_users(allowed_roles=['Broker', 'Customer']) |  |
| home | `/<str:IPOid>/Status` | Status | Status | POST branch; other verbs not necessarily rejected | allowed_users(allowed_roles=['Broker']) | Status.html |
| home | `/update-telly-status/` | update_telly_status | update_telly_status | No method decorator | csrf_exempt |  |
| home | `/GroupWiseDashboard` | GroupWiseDashboard | GroupWiseDashboard | POST branch; other verbs not necessarily rejected | allowed_users(allowed_roles=['Broker']) | GroupWiseDashboard.html |
| home | `/group-billing-details/` | group_billing_details | group_billing_details | No method decorator | No explicit decorator; inspect view/session checks | group_billing_details.html |
| home | `/group-billing-details/<int:group_id>/` | group_billing_details_by_id | group_billing_details | No method decorator | No explicit decorator; inspect view/session checks | group_billing_details.html |
| home | `/BackUp` | BackUp | BackUp | POST branch; other verbs not necessarily rejected | No explicit decorator; inspect view/session checks | Backup.html |
| home | `/panalloted` | panalloted | panalloted | No method decorator | allowed_users(allowed_roles=['Broker']) | panalloted.html |
| home | `/<str:IPOid>/<str:OrderType>/upload-csv/<str:GrpName>/<str:OrderCategory>/<str:InvestorType>/<str:OrderDate>/<str:OrderTime>` | OrderDetail_upload | OrderDetail_upload | No method decorator | No explicit decorator; inspect view/session checks |  |
| home | `/<str:IPOid>/<str:OrderType>/upload-csv/<str:GrpName>/<str:OrderCategory>/<str:InvestorType>/<str:OrderDate>/<str:OrderTime>/<str:Rate>` | OrderDetail_upload | OrderDetail_upload | No method decorator | No explicit decorator; inspect view/session checks |  |
| home | `/<str:IPOid>/upload-csv/<str:Groupfilter>/<str:Ordercatagoryfilter>/<str:InvestorTypefilter>` | Order_upload | Order_upload | No method decorator | No explicit decorator; inspect view/session checks |  |
| home | `/AddPayment` | AddPayment | AddPayment | POST branch; other verbs not necessarily rejected | allowed_users(allowed_roles=['Broker']) |  |
| home | `/login` | login | loginUser | POST branch; other verbs not necessarily rejected | No explicit decorator; inspect view/session checks | login.html |
| home | `/logout` | logout | logoutUser | No method decorator | No explicit decorator; inspect view/session checks |  |
| home | `/<str:IPOid>/ShareBill` | GroupWiseBillShare | GroupBillShare | POST branch; other verbs not necessarily rejected | No explicit decorator; inspect view/session checks |  |
| home | `/accounting/` | accounting | accounting_view | No method decorator | login_required | accounting.html |
| home | `/get-accounting-entries/` | get_accounting_entries | get_accounting_entries | No method decorator | No explicit decorator; inspect view/session checks |  |
| home | `/save_transaction/` | save_transaction | save_transaction | POST branch; other verbs not necessarily rejected | No explicit decorator; inspect view/session checks |  |
| home | `/save_transaction_group/` | save_transaction_group | save_transaction_group | POST branch; other verbs not necessarily rejected | No explicit decorator; inspect view/session checks |  |
| home | `/update-accounting/` | update_accounting | update_accounting | POST branch; other verbs not necessarily rejected | login_required |  |
| home | `/bulk-delete-accounting/` | bulk_delete_accounting | bulk_delete_accounting | No method decorator | login_required |  |
| home | `/soft-delete-accounting/<int:entry_id>/` | soft_delete_accounting | soft_delete_accounting | No method decorator | login_required; csrf_exempt |  |
| home | `/restore-accounting/<int:entry_id>/` | restore_accounting | restore_accounting | No method decorator | login_required; csrf_exempt |  |
| home | `/add-transaction/` | add_transaction | add_transaction | No method decorator | login_required | accounting/Accounting.html |
| home | `/add_transaction_group/` | add_transaction_group | add_transaction_group | No method decorator | login_required | GroupWiseDashboard.html |
| home | `/accounting-logs/` | accounting_logs | accounting_logs_view | No method decorator | login_required | accounting_logs.html |
| home | `/ipo_transaction/` | ipo_transaction | ipo_transaction | POST branch; other verbs not necessarily rejected | No explicit decorator; inspect view/session checks |  |
| home | `/ipo_transaction1 /` | ipo_transaction1 | ipo_transaction1 | POST branch; other verbs not necessarily rejected | No explicit decorator; inspect view/session checks |  |
| home | `/AccountingBackup/` | AccountingBackup | AccountingBackup | No method decorator | No explicit decorator; inspect view/session checks |  |
| home | `/share-records/` | Share_AppDetails | Share_AppDetails | POST branch; other verbs not necessarily rejected | csrf_exempt |  |
| home | `/user-profile/` | user_profile | user_profile | No method decorator | login_required | user_profile.html |
| home | `/update-user-profile/` | update_user_profile | update_user_profile | POST branch; other verbs not necessarily rejected | login_required |  |
| home | `/send-telegram-otp/` | send_telegram_otp | send_telegram_otp | No method decorator | csrf_exempt |  |
| home | `/verify-telegram-otp/` | verify_telegram_otp | verify_telegram_otp | POST branch; other verbs not necessarily rejected | csrf_exempt |  |
| home | `/place-order/<int:IPOid>/<str:order_type>/` | place_order | place_order_view | POST branch; other verbs not necessarily rejected | login_required; csrf_exempt |  |
| home | `/share-status-telegram/` | share_status_telegram | share_status_telegram | No method decorator | login_required; csrf_exempt |  |
| home | `/<str:IPOid>/send-status-telegram/` | send_status_to_telegram | send_status_to_telegram | No method decorator | login_required; csrf_exempt |  |
| home | `/<int:IPOid>/DeleteAllOrders/` | delete_all_orders | DeleteAllOrders | No method decorator | allowed_users(allowed_roles=['Broker']) |  |
| home | `/bulk_ipo_transactions/` | bulk_ipo_transactions | bulk_ipo_transactions | POST branch; other verbs not necessarily rejected | login_required |  |
| home | `/bulk-transfer-transactions/` | bulk_transfer_transactions | bulk_transfer_transactions | No method decorator | login_required |  |
| home | `/api/transfer-batch/<uuid:batch_id>/` | get_transfer_batch | get_transfer_batch | No method decorator | login_required |  |
| home | `/api/transfer-group-ipos/<int:group_id>/` | get_transfer_group_ipos | get_transfer_group_ipos | No method decorator | login_required |  |
| home | `/api/get-group-dues/<int:group_id>/` | get_group_dues | get_group_dues | No method decorator | login_required |  |
| home | `/<int:IPOid>/get-all-groups/` | get_all_groups | get_all_groups | No method decorator | No explicit decorator; inspect view/session checks |  |
| home | `/<str:IPOid>/send-status-telegram/` | send_status_to_telegram | send_status_to_telegram | No method decorator | login_required; csrf_exempt |  |
| home | `/<str:IPOid>/send-status-telegram-image/` | send_status_to_telegram_image | send_status_to_telegram_image | POST branch; other verbs not necessarily rejected | login_required; csrf_exempt |  |
| home | `/generate-shared-link/` | generate_shared_link | generate_shared_link | POST branch; other verbs not necessarily rejected | No explicit decorator; inspect view/session checks |  |
| home | `/access-link/<uuid:link_id>/` | resolve_shared_link | resolve_shared_link | POST branch; other verbs not necessarily rejected | No explicit decorator; inspect view/session checks |  |
| home | `/access-link/<uuid:link_id>/<str:order_type>` | resolve_shared_link | resolve_shared_link | POST branch; other verbs not necessarily rejected | No explicit decorator; inspect view/session checks |  |
| home | `/get-user-links/<int:IPOid>/<str:order_type>` | get_user_links | get_user_links | No method decorator | No explicit decorator; inspect view/session checks |  |
| home | `/delete-link/` | delete_link | delete_link | POST branch; other verbs not necessarily rejected | login_required |  |
| home | `/update-link/<uuid:link_id>/` | update_shared_link | update_shared_link | POST branch; other verbs not necessarily rejected | login_required |  |
| home | `/send-link-mail/<uuid:linkId>/` | send_link_mail | send_link_mail | No method decorator | No explicit decorator; inspect view/session checks |  |
| home | `/update-all-expiries/<int:IPOid>/` | update_all_expiries | update_all_expiries | POST branch; other verbs not necessarily rejected | No explicit decorator; inspect view/session checks |  |
| home | `/send-all-link-mails/<int:IPOid>/` | send_all_link_mails | send_all_link_mails | POST branch; other verbs not necessarily rejected | No explicit decorator; inspect view/session checks |  |
| home | `/bulk-generate-links/<str:IPOid>/` | bulk_generate_links | bulk_generate_links | POST branch; other verbs not necessarily rejected | No explicit decorator; inspect view/session checks |  |
| home | `/update-link-status/` | update_link_status | update_link_status | POST branch; other verbs not necessarily rejected | No explicit decorator; inspect view/session checks |  |
| home | `/<str:IPOid>/BulkDeleteOrders/` | BulkDeleteOrders | BulkDeleteOrders | No method decorator | csrf_exempt; allowed_users(allowed_roles=['Broker']) |  |
| home | `/BulkDeleteGroup` | BulkDeleteGroup | BulkDeleteGroup | No method decorator | allowed_users(allowed_roles=['Broker']) |  |
| home | `/BulkDeleteClients` | BulkDeleteClients | BulkDeleteClients | No method decorator | allowed_users(allowed_roles=['Broker']) |  |
| whatsapp | `/whatsapp/buy/<int:ipo_id>/send/` | send_buy_order | send_buy_order | POST only | login_required; require_POST |  |
| whatsapp | `/whatsapp/sell/<int:ipo_id>/send/` | send_sell_order | send_sell_order | POST only | login_required; require_POST |  |
