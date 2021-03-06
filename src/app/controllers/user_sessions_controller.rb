#
# Copyright 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

class UserSessionsController < ApplicationController
  before_filter :require_no_user, :only => [:new, :create]
  before_filter :require_user, :only => [:destroy, :set_org]
  skip_before_filter :require_org
  protect_from_forgery

  skip_before_filter :authorize # ok - need to skip all methods

  def section_id
    "loginpage"
  end

  def new
    if !request.env['HTTP_X_FORWARDED_USER'].blank?
      # if we received the X-Forwarded-User, the user must have logged in via SSO; therefore,
      # attempt to authenticate and log the user in now versus requiring them to enter 
      # credentials 
      login_user
    else
      @disable_password_recovery = AppConfig.warden == 'ldap'
      render "common/user_session", :layout => "converge-ui/login_layout"
    end
  end

  def create
    login_user
  end

  def destroy
    logout
    self.current_organization = nil
    notify.success _("Logout Successful"), :persist => false
    redirect_to root_url
  end

  def allowed_orgs
    render :partial=>"/layouts/allowed_orgs", :locals =>{:user=>current_user}
  end

  def set_org
    orgs = current_user.allowed_organizations
    org = Organization.find(params[:org_id])
    if org.nil? or !orgs.include?(org)
      notify.error _("Invalid organization")
      render :nothing => true
      return
    else
      self.current_organization = org
    end
    if self.current_organization == org
      respond_to do |format|
        format.html {redirect_to dashboard_index_path}
        format.js { render :js => "CUI.Login.Actions.redirecter('#{dashboard_index_url}')" }
      end
    end
  end

  private

  def login_user
    authenticate! :scope => :user
    if logged_in?

      #save the hash anchor if it exsts
      if params[:hash_anchor] and  session[:original_uri] and !session[:original_uri].index("#")
        session[:original_uri] +=  params[:hash_anchor]
      end

      # set the current user in the thread-local variable (before notification)
      User.current = current_user
      # set ldap roles
      current_user.set_ldap_roles if AppConfig.ldap_roles

      orgs = current_user.allowed_organizations
      user_default_org = nil
      if current_user.default_org && !current_user.default_org.nil?
        user_default_org = current_user.default_org
      end

      if current_organization.nil?
        if orgs.length == 1
          params[:org_id] = orgs[0].id
          # notice the user
          notify.success _("Login Successful")
          set_org
        elsif !user_default_org.nil? && orgs.include?(user_default_org)
          params[:org_id] = user_default_org.id
          # notice the user
          notify.success _("Login Successful, logging into '%s' ") % user_default_org.name
          set_org
        elsif orgs.length < 1
          # notice the user, please choose an org
          notify.success _("Login Successful, please contact administrator to get permission to access an organization.")
          render :partial =>"/user_sessions/interstitial.js.haml", :locals=> {:num_orgs => orgs.length, :redir_path => dashboard_index_path}
        else
          # notice the user, please choose an org
          notify.success _("Login Successful, please choose an Organization")
          render :partial =>"/user_sessions/interstitial.js.haml", :locals=> {:num_orgs => orgs.length, :redir_path => dashboard_index_path}
        end
      else
        # notice the user, please choose an org
        notify.success _("Login Successful, please choose an Organization")
        render :partial =>"/user_sessions/interstitial.js.haml", :locals=> {:num_orgs => orgs.length, :redir_path => dashboard_index_path}
      end
    end
  end

  # return simple 401 page (for API authentication errors)
  def return_401
    head :status => 401 and return false
  end

  def default_notify_options
    { :organization => nil }
  end

end
