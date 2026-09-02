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
	
	    static createFrom(source: any = {}) {
	        return new AccountStatus(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.platform = source["platform"];
	        this.account = source["account"];
	        this.isValid = source["isValid"];
	        this.msg = source["msg"];
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

