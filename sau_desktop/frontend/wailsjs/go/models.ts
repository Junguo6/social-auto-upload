export namespace auth {
	
	export class AuthOverview {
	    new_sn: string;
	    machine_id: string;
	    is_activated: boolean;
	    is_expired: boolean;
	    days_remaining: number;
	    deadline: string;
	    user_id: string;
	    version: string;
	    announcement: string;
	    help_url: string;
	    agent_notice: string;
	    agent_website: string;
	    m100_activated: boolean;
	    m122_activated: boolean;
	    m122_trial_times: number;
	    m122_month_price: string;
	    m122_season_price: string;
	    m122_year_price: string;
	    m122_permanent_price: string;
	    // Go type: time
	    last_check_time: any;
	
	    static createFrom(source: any = {}) {
	        return new AuthOverview(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.new_sn = source["new_sn"];
	        this.machine_id = source["machine_id"];
	        this.is_activated = source["is_activated"];
	        this.is_expired = source["is_expired"];
	        this.days_remaining = source["days_remaining"];
	        this.deadline = source["deadline"];
	        this.user_id = source["user_id"];
	        this.version = source["version"];
	        this.announcement = source["announcement"];
	        this.help_url = source["help_url"];
	        this.agent_notice = source["agent_notice"];
	        this.agent_website = source["agent_website"];
	        this.m100_activated = source["m100_activated"];
	        this.m122_activated = source["m122_activated"];
	        this.m122_trial_times = source["m122_trial_times"];
	        this.m122_month_price = source["m122_month_price"];
	        this.m122_season_price = source["m122_season_price"];
	        this.m122_year_price = source["m122_year_price"];
	        this.m122_permanent_price = source["m122_permanent_price"];
	        this.last_check_time = this.convertValues(source["last_check_time"], null);
	    }
	
		convertValues(a: any, classs: any, asMap: boolean = false): any {
		    if (!a) {
		        return a;
		    }
		    if (a.slice && a.map) {
		        return (a as any[]).map(elem => this.convertValues(elem, classs));
		    } else if ("object" === typeof a) {
		        if (asMap) {
		            for (const key of Object.keys(a)) {
		                a[key] = new classs(a[key]);
		            }
		            return a;
		        }
		        return new classs(a);
		    }
		    return a;
		}
	}
	export class OrderCreateResult {
	    success: boolean;
	    out_trade_no: string;
	    code_url: string;
	    message: string;
	
	    static createFrom(source: any = {}) {
	        return new OrderCreateResult(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.success = source["success"];
	        this.out_trade_no = source["out_trade_no"];
	        this.code_url = source["code_url"];
	        this.message = source["message"];
	    }
	}
	export class OrderPackage {
	    package_type: string;
	    label: string;
	    price_yuan: number;
	    amount_cent: number;
	    purchasable: boolean;
	
	    static createFrom(source: any = {}) {
	        return new OrderPackage(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.package_type = source["package_type"];
	        this.label = source["label"];
	        this.price_yuan = source["price_yuan"];
	        this.amount_cent = source["amount_cent"];
	        this.purchasable = source["purchasable"];
	    }
	}
	export class OrderQueryResult {
	    success: boolean;
	    trade_state: string;
	    trade_state_desc: string;
	
	    static createFrom(source: any = {}) {
	        return new OrderQueryResult(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.success = source["success"];
	        this.trade_state = source["trade_state"];
	        this.trade_state_desc = source["trade_state_desc"];
	    }
	}
	export class TrialConsumeResult {
	    ok: boolean;
	    message: string;
	    overview?: AuthOverview;
	
	    static createFrom(source: any = {}) {
	        return new TrialConsumeResult(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.ok = source["ok"];
	        this.message = source["message"];
	        this.overview = this.convertValues(source["overview"], AuthOverview);
	    }
	
		convertValues(a: any, classs: any, asMap: boolean = false): any {
		    if (!a) {
		        return a;
		    }
		    if (a.slice && a.map) {
		        return (a as any[]).map(elem => this.convertValues(elem, classs));
		    } else if ("object" === typeof a) {
		        if (asMap) {
		            for (const key of Object.keys(a)) {
		                a[key] = new classs(a[key]);
		            }
		            return a;
		        }
		        return new classs(a);
		    }
		    return a;
		}
	}

}

export namespace engine {
	
	export class AccountPublishResult {
	    taskId: string;
	    platform: string;
	    account: string;
	    success: boolean;
	    errorMsg: string;
	
	    static createFrom(source: any = {}) {
	        return new AccountPublishResult(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.taskId = source["taskId"];
	        this.platform = source["platform"];
	        this.account = source["account"];
	        this.success = source["success"];
	        this.errorMsg = source["errorMsg"];
	    }
	}
	export class AccountPublishTask {
	    taskId: string;
	    platform: string;
	    account: string;
	    nickname: string;
	    action: string;
	    filePath: string;
	    images: string[];
	    title: string;
	    desc: string;
	    tags: string;
	    thumbnail: string;
	    thumbnailLandscape: string;
	    thumbnailPortrait: string;
	    tid: number;
	    shortTitle: string;
	    category: string;
	    draft: boolean;
	    schedule: string;
	    declaration: string;
	    collection: string;
	    productLink: string;
	    productTitle: string;
	    visibility: string;
	    playlist: string;
	    bgm: string;
	    note: string;
	    notef: string;
	    location: string;
	    linkType: string;
	    linkUrl: string;
	    linkTitle: string;
	    activityName: string;
	    initialDelaySeconds: number;
	    delaySeconds: number;
	    headless: boolean;
	
	    static createFrom(source: any = {}) {
	        return new AccountPublishTask(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.taskId = source["taskId"];
	        this.platform = source["platform"];
	        this.account = source["account"];
	        this.nickname = source["nickname"];
	        this.action = source["action"];
	        this.filePath = source["filePath"];
	        this.images = source["images"];
	        this.title = source["title"];
	        this.desc = source["desc"];
	        this.tags = source["tags"];
	        this.thumbnail = source["thumbnail"];
	        this.thumbnailLandscape = source["thumbnailLandscape"];
	        this.thumbnailPortrait = source["thumbnailPortrait"];
	        this.tid = source["tid"];
	        this.shortTitle = source["shortTitle"];
	        this.category = source["category"];
	        this.draft = source["draft"];
	        this.schedule = source["schedule"];
	        this.declaration = source["declaration"];
	        this.collection = source["collection"];
	        this.productLink = source["productLink"];
	        this.productTitle = source["productTitle"];
	        this.visibility = source["visibility"];
	        this.playlist = source["playlist"];
	        this.bgm = source["bgm"];
	        this.note = source["note"];
	        this.notef = source["notef"];
	        this.location = source["location"];
	        this.linkType = source["linkType"];
	        this.linkUrl = source["linkUrl"];
	        this.linkTitle = source["linkTitle"];
	        this.activityName = source["activityName"];
	        this.initialDelaySeconds = source["initialDelaySeconds"];
	        this.delaySeconds = source["delaySeconds"];
	        this.headless = source["headless"];
	    }
	}
	export class AccountStatus {
	    platform: string;
	    account: string;
	    isValid: boolean;
	    msg: string;
	    avatar?: string;
	    nickname?: string;
	    finderUid?: string;
	
	    static createFrom(source: any = {}) {
	        return new AccountStatus(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.platform = source["platform"];
	        this.account = source["account"];
	        this.isValid = source["isValid"];
	        this.msg = source["msg"];
	        this.avatar = source["avatar"];
	        this.nickname = source["nickname"];
	        this.finderUid = source["finderUid"];
	    }
	}
	export class TargetAccount {
	    platform: string;
	    account: string;
	
	    static createFrom(source: any = {}) {
	        return new TargetAccount(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.platform = source["platform"];
	        this.account = source["account"];
	    }
	}
	export class BatchPublishParam {
	    targets: TargetAccount[];
	    concurrency: number;
	    action: string;
	    filePath: string;
	    images: string[];
	    title: string;
	    desc: string;
	    tags: string;
	    thumbnail: string;
	    thumbnailLandscape: string;
	    thumbnailPortrait: string;
	    tid: number;
	    shortTitle: string;
	    category: string;
	    draft: boolean;
	    schedule: string;
	    declaration: string;
	    collection: string;
	    productLink: string;
	    productTitle: string;
	    visibility: string;
	    playlist: string;
	    bgm: string;
	    note: string;
	    notef: string;
	    location: string;
	    linkType: string;
	    linkUrl: string;
	    linkTitle: string;
	    activityName: string;
	    headless: boolean;
	
	    static createFrom(source: any = {}) {
	        return new BatchPublishParam(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.targets = this.convertValues(source["targets"], TargetAccount);
	        this.concurrency = source["concurrency"];
	        this.action = source["action"];
	        this.filePath = source["filePath"];
	        this.images = source["images"];
	        this.title = source["title"];
	        this.desc = source["desc"];
	        this.tags = source["tags"];
	        this.thumbnail = source["thumbnail"];
	        this.thumbnailLandscape = source["thumbnailLandscape"];
	        this.thumbnailPortrait = source["thumbnailPortrait"];
	        this.tid = source["tid"];
	        this.shortTitle = source["shortTitle"];
	        this.category = source["category"];
	        this.draft = source["draft"];
	        this.schedule = source["schedule"];
	        this.declaration = source["declaration"];
	        this.collection = source["collection"];
	        this.productLink = source["productLink"];
	        this.productTitle = source["productTitle"];
	        this.visibility = source["visibility"];
	        this.playlist = source["playlist"];
	        this.bgm = source["bgm"];
	        this.note = source["note"];
	        this.notef = source["notef"];
	        this.location = source["location"];
	        this.linkType = source["linkType"];
	        this.linkUrl = source["linkUrl"];
	        this.linkTitle = source["linkTitle"];
	        this.activityName = source["activityName"];
	        this.headless = source["headless"];
	    }
	
		convertValues(a: any, classs: any, asMap: boolean = false): any {
		    if (!a) {
		        return a;
		    }
		    if (a.slice && a.map) {
		        return (a as any[]).map(elem => this.convertValues(elem, classs));
		    } else if ("object" === typeof a) {
		        if (asMap) {
		            for (const key of Object.keys(a)) {
		                a[key] = new classs(a[key]);
		            }
		            return a;
		        }
		        return new classs(a);
		    }
		    return a;
		}
	}
	export class BrowserEnvironmentInfo {
	    isReady: boolean;
	    browserType: string;
	    path: string;
	    summary: string;
	
	    static createFrom(source: any = {}) {
	        return new BrowserEnvironmentInfo(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.isReady = source["isReady"];
	        this.browserType = source["browserType"];
	        this.path = source["path"];
	        this.summary = source["summary"];
	    }
	}
	export class LoginResult {
	    success: boolean;
	    platform: string;
	    account: string;
	    nickname: string;
	    finderUid: string;
	    avatar?: string;
	    msg: string;
	
	    static createFrom(source: any = {}) {
	        return new LoginResult(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.success = source["success"];
	        this.platform = source["platform"];
	        this.account = source["account"];
	        this.nickname = source["nickname"];
	        this.finderUid = source["finderUid"];
	        this.avatar = source["avatar"];
	        this.msg = source["msg"];
	    }
	}
	export class MatrixPublishParam {
	    concurrency: number;
	    tasks: AccountPublishTask[];
	
	    static createFrom(source: any = {}) {
	        return new MatrixPublishParam(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.concurrency = source["concurrency"];
	        this.tasks = this.convertValues(source["tasks"], AccountPublishTask);
	    }
	
		convertValues(a: any, classs: any, asMap: boolean = false): any {
		    if (!a) {
		        return a;
		    }
		    if (a.slice && a.map) {
		        return (a as any[]).map(elem => this.convertValues(elem, classs));
		    } else if ("object" === typeof a) {
		        if (asMap) {
		            for (const key of Object.keys(a)) {
		                a[key] = new classs(a[key]);
		            }
		            return a;
		        }
		        return new classs(a);
		    }
		    return a;
		}
	}
	export class PipelineTaskLane {
	    laneId: string;
	    laneName: string;
	    tasks: AccountPublishTask[];
	    delayBetweenTasks: number;
	    scheduledAt: string;
	
	    static createFrom(source: any = {}) {
	        return new PipelineTaskLane(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.laneId = source["laneId"];
	        this.laneName = source["laneName"];
	        this.tasks = this.convertValues(source["tasks"], AccountPublishTask);
	        this.delayBetweenTasks = source["delayBetweenTasks"];
	        this.scheduledAt = source["scheduledAt"];
	    }
	
		convertValues(a: any, classs: any, asMap: boolean = false): any {
		    if (!a) {
		        return a;
		    }
		    if (a.slice && a.map) {
		        return (a as any[]).map(elem => this.convertValues(elem, classs));
		    } else if ("object" === typeof a) {
		        if (asMap) {
		            for (const key of Object.keys(a)) {
		                a[key] = new classs(a[key]);
		            }
		            return a;
		        }
		        return new classs(a);
		    }
		    return a;
		}
	}
	export class PipelinePublishParam {
	    lanes: PipelineTaskLane[];
	
	    static createFrom(source: any = {}) {
	        return new PipelinePublishParam(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.lanes = this.convertValues(source["lanes"], PipelineTaskLane);
	    }
	
		convertValues(a: any, classs: any, asMap: boolean = false): any {
		    if (!a) {
		        return a;
		    }
		    if (a.slice && a.map) {
		        return (a as any[]).map(elem => this.convertValues(elem, classs));
		    } else if ("object" === typeof a) {
		        if (asMap) {
		            for (const key of Object.keys(a)) {
		                a[key] = new classs(a[key]);
		            }
		            return a;
		        }
		        return new classs(a);
		    }
		    return a;
		}
	}
	
	export class PublishParam {
	    platform: string;
	    action: string;
	    account: string;
	    filePath: string;
	    images: string[];
	    title: string;
	    desc: string;
	    tags: string;
	    thumbnail: string;
	    thumbnailLandscape: string;
	    thumbnailPortrait: string;
	    tid: number;
	    shortTitle: string;
	    category: string;
	    draft: boolean;
	    schedule: string;
	    declaration: string;
	    collection: string;
	    productLink: string;
	    productTitle: string;
	    visibility: string;
	    playlist: string;
	    bgm: string;
	    note: string;
	    notef: string;
	    location: string;
	    linkType: string;
	    linkUrl: string;
	    linkTitle: string;
	    activityName: string;
	    headless: boolean;
	
	    static createFrom(source: any = {}) {
	        return new PublishParam(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.platform = source["platform"];
	        this.action = source["action"];
	        this.account = source["account"];
	        this.filePath = source["filePath"];
	        this.images = source["images"];
	        this.title = source["title"];
	        this.desc = source["desc"];
	        this.tags = source["tags"];
	        this.thumbnail = source["thumbnail"];
	        this.thumbnailLandscape = source["thumbnailLandscape"];
	        this.thumbnailPortrait = source["thumbnailPortrait"];
	        this.tid = source["tid"];
	        this.shortTitle = source["shortTitle"];
	        this.category = source["category"];
	        this.draft = source["draft"];
	        this.schedule = source["schedule"];
	        this.declaration = source["declaration"];
	        this.collection = source["collection"];
	        this.productLink = source["productLink"];
	        this.productTitle = source["productTitle"];
	        this.visibility = source["visibility"];
	        this.playlist = source["playlist"];
	        this.bgm = source["bgm"];
	        this.note = source["note"];
	        this.notef = source["notef"];
	        this.location = source["location"];
	        this.linkType = source["linkType"];
	        this.linkUrl = source["linkUrl"];
	        this.linkTitle = source["linkTitle"];
	        this.activityName = source["activityName"];
	        this.headless = source["headless"];
	    }
	}
	export class RiskState {
	    platform: string;
	    account: string;
	    // Go type: time
	    lastStartedAt: any;
	    // Go type: time
	    lastFinishedAt: any;
	    hourlyCount: number;
	    dailyCount: number;
	    // Go type: time
	    lastCountReset: any;
	    consecutiveFailures: number;
	    // Go type: time
	    cooldownUntil: any;
	    lastRiskCode: string;
	    paused: boolean;
	    pauseReason: string;
	
	    static createFrom(source: any = {}) {
	        return new RiskState(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.platform = source["platform"];
	        this.account = source["account"];
	        this.lastStartedAt = this.convertValues(source["lastStartedAt"], null);
	        this.lastFinishedAt = this.convertValues(source["lastFinishedAt"], null);
	        this.hourlyCount = source["hourlyCount"];
	        this.dailyCount = source["dailyCount"];
	        this.lastCountReset = this.convertValues(source["lastCountReset"], null);
	        this.consecutiveFailures = source["consecutiveFailures"];
	        this.cooldownUntil = this.convertValues(source["cooldownUntil"], null);
	        this.lastRiskCode = source["lastRiskCode"];
	        this.paused = source["paused"];
	        this.pauseReason = source["pauseReason"];
	    }
	
		convertValues(a: any, classs: any, asMap: boolean = false): any {
		    if (!a) {
		        return a;
		    }
		    if (a.slice && a.map) {
		        return (a as any[]).map(elem => this.convertValues(elem, classs));
		    } else if ("object" === typeof a) {
		        if (asMap) {
		            for (const key of Object.keys(a)) {
		                a[key] = new classs(a[key]);
		            }
		            return a;
		        }
		        return new classs(a);
		    }
		    return a;
		}
	}

}

export namespace main {
	
	export class ScannedMediaItem {
	    filePath: string;
	    fileName: string;
	    parentFolder: string;
	    childFolder: string;
	    folders: string[];
	    sizeBytes: number;
	    fileSizeText: string;
	    episode: number;
	
	    static createFrom(source: any = {}) {
	        return new ScannedMediaItem(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.filePath = source["filePath"];
	        this.fileName = source["fileName"];
	        this.parentFolder = source["parentFolder"];
	        this.childFolder = source["childFolder"];
	        this.folders = source["folders"];
	        this.sizeBytes = source["sizeBytes"];
	        this.fileSizeText = source["fileSizeText"];
	        this.episode = source["episode"];
	    }
	}
	export class FolderScanResult {
	    root: string;
	    valid: boolean;
	    message: string;
	    warnings: string[];
	    parentCount: number;
	    childCount: number;
	    videoCount: number;
	    items: ScannedMediaItem[];
	
	    static createFrom(source: any = {}) {
	        return new FolderScanResult(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.root = source["root"];
	        this.valid = source["valid"];
	        this.message = source["message"];
	        this.warnings = source["warnings"];
	        this.parentCount = source["parentCount"];
	        this.childCount = source["childCount"];
	        this.videoCount = source["videoCount"];
	        this.items = this.convertValues(source["items"], ScannedMediaItem);
	    }
	
		convertValues(a: any, classs: any, asMap: boolean = false): any {
		    if (!a) {
		        return a;
		    }
		    if (a.slice && a.map) {
		        return (a as any[]).map(elem => this.convertValues(elem, classs));
		    } else if ("object" === typeof a) {
		        if (asMap) {
		            for (const key of Object.keys(a)) {
		                a[key] = new classs(a[key]);
		            }
		            return a;
		        }
		        return new classs(a);
		    }
		    return a;
		}
	}

}

export namespace upgrade {
	
	export class VersionInfo {
	    id?: string;
	    tool_id?: string;
	    version: string;
	    desc: string;
	    brief: string;
	    is_pop_up: boolean;
	    is_official: boolean;
	    is_forced: boolean;
	    created_at: string;
	    updated_at?: string;
	
	    static createFrom(source: any = {}) {
	        return new VersionInfo(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.id = source["id"];
	        this.tool_id = source["tool_id"];
	        this.version = source["version"];
	        this.desc = source["desc"];
	        this.brief = source["brief"];
	        this.is_pop_up = source["is_pop_up"];
	        this.is_official = source["is_official"];
	        this.is_forced = source["is_forced"];
	        this.created_at = source["created_at"];
	        this.updated_at = source["updated_at"];
	    }
	}
	export class CheckUpdateResult {
	    has_update: boolean;
	    current_version: string;
	    latest_version: string;
	    version_info?: VersionInfo;
	    message: string;
	    // Go type: time
	    check_time: any;
	
	    static createFrom(source: any = {}) {
	        return new CheckUpdateResult(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.has_update = source["has_update"];
	        this.current_version = source["current_version"];
	        this.latest_version = source["latest_version"];
	        this.version_info = this.convertValues(source["version_info"], VersionInfo);
	        this.message = source["message"];
	        this.check_time = this.convertValues(source["check_time"], null);
	    }
	
		convertValues(a: any, classs: any, asMap: boolean = false): any {
		    if (!a) {
		        return a;
		    }
		    if (a.slice && a.map) {
		        return (a as any[]).map(elem => this.convertValues(elem, classs));
		    } else if ("object" === typeof a) {
		        if (asMap) {
		            for (const key of Object.keys(a)) {
		                a[key] = new classs(a[key]);
		            }
		            return a;
		        }
		        return new classs(a);
		    }
		    return a;
		}
	}
	export class DownloadProgress {
	    percentage: number;
	    downloaded: number;
	    total: number;
	    downloaded_mb: number;
	    total_mb: number;
	    status: string;
	    message?: string;
	    error?: string;
	
	    static createFrom(source: any = {}) {
	        return new DownloadProgress(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.percentage = source["percentage"];
	        this.downloaded = source["downloaded"];
	        this.total = source["total"];
	        this.downloaded_mb = source["downloaded_mb"];
	        this.total_mb = source["total_mb"];
	        this.status = source["status"];
	        this.message = source["message"];
	        this.error = source["error"];
	    }
	}

}

